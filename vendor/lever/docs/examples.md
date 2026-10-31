# Examples

Illustrative exchanges, abbreviated. The numbers are made up; the shapes are real. Each card is one command and roughly what comes back.

Everything is `/lever <verb> <your ask>`. Don't know the verb? `/lever <your ask>`.

## Front door

![/lever <verb> <your words>](examples/try.png)

![/lever](examples/lever.png)

## Loop: make an existing thing measurably better

![/lever loop](examples/loop.png)

![/lever arms](examples/arms.png)

![/lever review](examples/review.png)

## Build: something new, no signal yet

![/lever brief](examples/brief.png)

![/lever refactor](examples/refactor.png)

## Build: getting work landed

![/lever shepherd](examples/shepherd.png)

## Run: work that should happen without you

![/lever automate](examples/automate.png)

## You: tune lever to how you work

![/lever mirror](examples/mirror.png)

![/lever steer](examples/steer.png)

![/lever autonomy](examples/autonomy.png)

---

The cards are rendered from [`examples/examples.html`](examples/examples.html). To change one, edit the HTML and run:

```bash
NODE_PATH=/path/to/node_modules node docs/examples/render.mjs   # needs playwright, @fontsource/mona-sans, @fontsource/monaspace-neon
```
