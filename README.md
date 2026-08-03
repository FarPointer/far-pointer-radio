# far-pointer-radio

A monorepo for radio show production, tooling, and related content.

## Projects

### [Convergence Zone](https://convergencezone.fm)

An independent radio program. Show content, playlists, one sheets, website assets, and production notes live under [`shows/convergence-zone/`](shows/convergence-zone/).

### KSER

Volunteer work for [KSER 90.7 FM](https://www.kser.org). Files live under [`shows/kser/`](shows/kser/).

### KEXP

Volunteer work for [KEXP 90.3 FM](https://www.kexp.org). Files live under [`shows/kexp/`](shows/kexp/).

## Repository Layout

```
far-pointer-radio/
├── shows/
│   ├── convergence-zone/   # Convergence Zone show materials
│   │   ├── playlists/      # Episode playlists (Spinitron exports, CSV, etc.)
│   │   ├── one-sheets/     # Artist/episode one sheets
│   │   ├── website/        # WordPress theme overrides, assets, copy
│   │   └── docs/           # Show notes, rundowns, SOPs
│   ├── kser/               # KSER volunteer materials
│   └── kexp/               # KEXP volunteer materials
├── tools/                  # Custom scripts and forked utilities
│   ├── python/             # Python scripts and packages
│   └── powershell/         # PowerShell scripts and modules
├── config/                 # Tool and service configuration
│   ├── spinitron/          # Spinitron API config and templates
│   └── vscode/             # Shared VS Code workspace settings
└── docs/                   # Project-wide documentation
```

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
Python scripts require Python 3.9+. See individual `README.md` files within each subdirectory for setup instructions.

## Contributing

This is a personal/volunteer working repository. If you're a collaborator, please create a feature branch and open a pull request for any significant changes.
