"""Stage a promoted experiment tree in a clean, exclusively owned delivery worktree.

This module is invoked under the experiment controller lock. It does not commit,
publish, or authenticate user-supplied semantic judgments. The caller must own
and quiesce the delivery worktree; its Git metadata is not a sandbox.
"""
from pathlib import Path
import os
import subprocess
import tempfile

from experiment_git import _environment, _inside_scope, _names, _paths, _run


def _delivery_git(delivery, *args, index=None, text=True):
    env = _environment()
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    try:
        result = subprocess.run(
            ['git', '-c', f'core.hooksPath={os.devnull}', '-c', 'core.fsmonitor=false',
             '-c', 'credential.helper=', '-C', str(delivery), *map(str, args)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text,
            check=False, timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError('delivery Git command timed out; inspect the delivery worktree') from error
    if result.returncode:
        detail = result.stderr if text else result.stderr.decode('utf-8', 'replace')
        raise ValueError('delivery Git command failed: ' + detail.strip())
    return result.stdout


def _assessment(core, root, config, saved, base, candidate, generation, split):
    spec = core.evaluation_spec(config, base, candidate, split)
    before = core.rows_for(root, config, saved['baseline_keys'], 'baseline', base,
                           split, revision=core.config_digest(root), generation=generation)
    after = core.rows_for(root, config, saved['candidate_keys'], 'candidate', candidate,
                          split, revision=core.config_digest(root), generation=generation)
    result = core.compare(spec, before, after, root / 'evidence')
    return {'result': result, 'spec': spec, 'baseline': before, 'candidate': after}


def handoff_locked(core, root, config, git, decision_id, delivery):
    """Verify and stage a promoted tree, holding the caller's controller lock."""
    decision_id = core.name(decision_id)
    experiment = config['experiment']
    intent = core.load_promotion_intent(root, decision_id)
    saved = core.validate_promotion_intent(root, config, git, decision_id, intent)
    base = core.commit_identity(git, intent['expected'])
    candidate = core.commit_identity(git, intent['candidate'])
    completed = core.read(root / 'promotions' / (decision_id + '.completed.json'))
    if completed != {'expected': base['commit'], 'candidate': candidate['commit'], 'state': 'completed'}:
        raise ValueError('promotion has not completed')
    if (git.resolve_integration(experiment) != candidate['commit'] or
            git.promotion_marker(experiment, decision_id) != candidate['commit'] or
            git.generation(experiment) != intent['new_generation']):
        raise ValueError('promoted ref, generation or marker changed')
    assessment = _assessment(core, root, config, saved, base, candidate,
                             intent['expected_generation'], 'selection')
    if assessment != {key: saved[key] for key in ('result', 'spec', 'baseline', 'candidate')}:
        raise ValueError('selection evidence changed since promotion')
    if assessment['result']['decision'] != 'eligible':
        raise ValueError('selection is not eligible')
    provenance = {'selection': [row['provenance'] for row in assessment['candidate']]}
    if 'confirmation' in config:
        suffix = intent['expected_generation'] + '-' + core.config_digest(root) + '.json'
        selection_path = root / 'selections' / suffix
        selection = core.read(selection_path)
        confirmation = core.read(root / 'confirmations' / suffix)
        if (selection['decision'] != decision_id or
                selection['decision_digest'] != core.digest(root / 'decisions' / (decision_id + '.json')) or
                selection['config_digest'] != core.config_digest(root) or
                confirmation['selection_digest'] != core.digest(selection_path)):
            raise ValueError('confirmation does not match the promoted decision')
        verified = _assessment(core, root, config, confirmation, base, candidate,
                               intent['expected_generation'], 'confirmation')
        if (verified['result']['decision'] != 'eligible' or
                verified != {key: confirmation[key] for key in ('result', 'spec', 'baseline', 'candidate')}):
            raise ValueError('confirmation evidence changed since promotion')
        provenance['confirmation'] = [row['provenance'] for row in verified['candidate']]

    delivery = Path(delivery).resolve(strict=True)
    top = Path(_delivery_git(delivery, 'rev-parse', '--show-toplevel').rstrip('\n')).resolve()
    if delivery != top or delivery.is_relative_to(root) or root.is_relative_to(delivery):
        raise ValueError('delivery must be a separate worktree root outside the private experiment')
    git._check_filters(worktree=delivery)
    status_args = ('status', '--porcelain=v1', '--untracked-files=all', '--ignored=matching')
    if _delivery_git(delivery, *status_args):
        raise ValueError('delivery worktree must be clean, including ignored files')
    head = _delivery_git(delivery, 'rev-parse', '--verify', 'HEAD^{commit}').strip()
    if head != base['commit']:
        raise ValueError('delivery HEAD changed; prepare and re-evaluate an integration candidate')
    if git._git('merge-base', '--is-ancestor', base['commit'], candidate['commit'], check=False).returncode:
        raise ValueError('champion does not descend from the evaluation baseline')
    changed = git._git('diff', '--no-ext-diff', '--no-textconv', '--name-only', '--no-renames',
                       '-z', base['commit'], candidate['commit'], text=False).stdout
    paths = _names(changed)
    allowed = _paths(config['paths'])
    if not paths or any(not _inside_scope(path, allowed) for path in paths):
        raise ValueError('candidate changes are empty or outside the configured edit paths')
    diff = git._git('diff', '--no-ext-diff', '--no-textconv', '--binary', '--full-index',
                    '--no-renames', base['commit'], candidate['commit'], text=False).stdout
    with tempfile.TemporaryDirectory(prefix='tkstack-handoff-') as tmp:
        patch = Path(tmp) / 'candidate.patch'
        patch.write_bytes(diff)
        _delivery_git(delivery, 'fetch', '--no-tags', '--no-write-fetch-head', '--no-auto-maintenance',
                      git.repo, candidate['commit'])
        fetched_tree = _delivery_git(delivery, 'rev-parse', '--verify', candidate['commit'] + '^{tree}').strip()
        if fetched_tree != candidate['tree']:
            raise ValueError('fetched candidate tree differs')
        index = Path(tmp) / 'index'
        _delivery_git(delivery, 'read-tree', base['commit'], index=index)
        _delivery_git(delivery, 'apply', '--cached', '--binary', patch, index=index)
        if _delivery_git(delivery, 'write-tree', index=index).strip() != candidate['tree']:
            raise ValueError('integration would change the evaluated tree; re-evaluation is required')
        if (_delivery_git(delivery, 'rev-parse', '--verify', 'HEAD^{commit}').strip() != base['commit'] or
                _delivery_git(delivery, *status_args)):
            raise ValueError('delivery worktree changed during preparation')
        git._check_filters(worktree=delivery)
        _delivery_git(delivery, 'apply', '--check', '--index', '--binary', patch)
        _delivery_git(delivery, 'apply', '--index', '--binary', patch)
        actual = _delivery_git(delivery, 'write-tree').strip()
        if actual != candidate['tree']:
            raise ValueError('staged tree differs; inspect and re-evaluate before delivery')
    return {'baseline': base['commit'], 'champion': candidate['commit'], 'tree': actual,
            'paths': paths, 'state': 'staged', 'provenance': provenance, 'limitations':
            'No commit or publication was made. Inspect evidence and re-evaluate if integration context changes.'}
