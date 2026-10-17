# Audio Generation Pipeline: agent instructions

Local speech and sound generation on the Mac Studio and the Art PC (RTX 3090). Read
[README.md](./README.md) for layout and commands, and [docs/models.md](docs/models.md) for
where each model lives.

<!-- BEGIN:generation-family -->
## Sibling repos

This repo is one of four related repos for AI-generated film work: images, video, audio, and
continuity repair. They stay separate on purpose (different stacks, no shared code). The same
block sits in all four AGENTS.md files between the `generation-family` markers; change it in
all four or in none.

| Repo | Local folder (always quote) | What it does | Stack |
|---|---|---|---|
| Film Design System | `~/ClaudeCode Projects/Image Generation Pipeline ` (trailing space) | Canon of characters, props and settings with curated reference images; image generation against it | Next.js, SQLite, Gemini |
| Video Generation Pipeline | `~/ClaudeCode Projects/Video Generation Pileline` ("Pileline" is the real folder name) | Seedance and Runway clients; reference packs in `library/` | Python CLI |
| Audio Generation Pipeline | `~/ClaudeCode Projects/Audio-Generation-Pipeline` | Speech (Qwen3-TTS, Higgs Audio v2), voice cloning, sound effects, on the Mac Studio and the Art PC | Python, shell, PowerShell |
| Continuity Lab | `~/ClaudeCode Projects/Video Lab` | Find and repair inconsistencies between generated video shots | Next.js, SQLite, ffmpeg |

GitHub, all under `weeeha/`: `Image-Generation-Pipeline-` (trailing dash),
`Video-Generation-Pipeline` and `Audio-Generation-Pipeline` are public; `Video-Lab` is private.

### How they connect

No code or data path links them yet; files move by hand. Known and planned links:

- **Image → video (planned).** The Film Design System spec names Seedance reference-to-video
  as a later consumer of its canon. The video repo's `library/<category>/<name>/` packs
  (`refs/` + `card.md`) hold the same kind of thing as folders, so an export from the canon
  would land there.
- **Video → Continuity Lab.** The Lab imports existing clips into a project folder. Its own
  generation backend (`seedance-fal`, via fal.ai) is planned for its plan 5 and is separate
  from the BytePlus client in the video repo.
- **Audio → video (open).** Seedance 2.5 accepts audio references and the audio repo makes
  voices and effects, but no step connects them. The audio repo also serves OpenClaw's
  Speaker agent, which is unrelated to film work.

### Working across repos

- Read the sibling's own AGENTS.md (or README) before changing it. Spend rules differ: image
  and video generations cost money and need Nick's go; audio runs on the Art PC GPU and can
  pause llama-server while it runs.
- Don't copy code between repos. When a shared format appears (a canon export, say),
  document it in both repos it connects and update this block.
- Branch per task in each repo; never push to `main`.
<!-- END:generation-family -->
