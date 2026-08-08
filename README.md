# far-pointer-radio

A monorepo for radio show production, tooling, and related content.

## Projects

### [Convergence Zone](https://convergencezone.fm)

An independent radio program. Show content, playlists, one sheets, website assets, and production notes live under [`shows/convergence-zone/`](shows/convergence-zone/).

### KSER

Projects for [KSER 90.7 FM](https://www.kser.org) and its non-profit — website work, volunteering, logistics, board work, and more. Files live under [`stations/kser/`](stations/kser/).

### KEXP

Projects for [KEXP 90.3 FM](https://www.kexp.org) and its non-profit — website work, volunteering, logistics, board work, and more. Files live under [`stations/kexp/`](stations/kexp/).

## Repository Layout

```
far-pointer-radio/
├── shows/
│   └── convergence-zone/       # Convergence Zone show materials
│       ├── playlists/          # Episode playlists (Spinitron exports, CSV, etc.)
│       ├── website/            # Design mockups from an earlier (paused) rebuild exploration
│       ├── images/             # Show images (logos, banners, photos)
│       └── docs/               # Show notes, rundowns, SOPs
│           └── press-kit/      # One sheets, bios, press materials
│               └── images/     # Images for press kit materials
├── stations/
│   ├── kser/                   # KSER station projects (website, volunteering, board, etc.)
│   │   └── images/             # KSER images
│   └── kexp/                   # KEXP station projects (website, volunteering, board, etc.)
│       └── images/             # KEXP images
├── tools/                      # Custom scripts and forked utilities
│   ├── python/                 # Python scripts and packages
│   └── powershell/             # PowerShell scripts and modules
├── .github/                    # Agent instructions, skills, workflows, PR template
│   ├── instructions/           # Path-scoped agent rules (applyTo globs)
│   ├── skills/                 # Repository-specific agent skills
│   └── workflows/              # GitHub Actions
├── docs/                       # Project-wide documentation
└── discarded/                  # Superseded prototypes retained for context, not use
```

Editor configuration lives in `far-pointer-radio.code-workspace`, `.editorconfig`, and
`.vscode/`. Service credentials live outside the repository — see `AGENTS.md`.

## Tools & Platforms

| Category | Tools |
|---|---|
| AI / Coding | Claude Code CLI · Claude (macOS) · GitHub Copilot (CLI / Web / VS Code) |
| Languages | Python · PowerShell · Bash / Zsh |
| Audio DAW | Reaper · Adobe Audition · Audacity · GarageBand |
| Audio AI | Adobe Podcast AI |
| Video | Final Cut Pro |
| Hardware | Logitech G-Hub |
| Playlist mgmt | Spinitron |
| CMS | WordPress |
| Editor | Visual Studio Code |
| Office | Excel |
| Platforms | Windows · macOS · Linux · iOS |

## Getting Started

Clone the repo and navigate to the relevant show or tool directory.  
Python tooling requires Python 3.11+ and [`uv`](https://docs.astral.sh/uv/). Run it through
the task runner in `tools/python/` (`make build`, `make verify`, `make all`). See
individual `README.md` files within each subdirectory for setup instructions, and
`CONTRIBUTING.md` for the working conventions.

## Contributing

This is a personal/volunteer working repository. If you're a collaborator, please create a feature branch and open a pull request for any significant changes. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the conventions and
[`docs/operating-procedures.md`](docs/operating-procedures.md) for the recurring workflows.

Agent guidance lives in [`AGENTS.md`](AGENTS.md), with path-scoped rules in
`.github/instructions/` and repeatable procedures in `.github/skills/`.
