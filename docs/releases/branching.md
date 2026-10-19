# Branches, tags and porting

Reco2Pico follows the CMSSW model: development happens on `main`, which tracks
the newest CMSSW release cycle, and each older release cycle that is still used
gets its own branch named after the cycle, `CMSSW_<major>_<minor>_X`. Exact
versions are tags. Shared work moves between branches by cherry-pick. The
branches in use right now are listed in the top-level [README](../../README.md).

In the commands below, `<branch>` is a release branch such as `CMSSW_15_0_X`,
`<tag>` a version tag such as `v1.4.0_CMSSW_15_0_X`, and `<sha>` a commit id.

## 1. Git basics: branches develop, tags reproduce

| concept | what it is | moves? | use it for |
|---|---|---|---|
| commit | one snapshot of the code, with an id (sha) | never | a unit of change |
| branch | a named line of development, pointing at its newest commit | yes, every commit moves it | ongoing work for one CMSSW release cycle |
| tag | a permanent name for one exact commit | never | "this exact code produced this Pico production" |
| GitHub Release | a tag plus release notes on the GitHub page | never | telling people what changed |

A tag points at the same code forever. A branch name does not, because the
branch keeps moving.

## 2. How CMSSW itself organizes releases

CMSSW (github.com/cms-sw/cmssw) develops on `master` and opens one branch per
release cycle. Every release is a tag.

| name pattern | kind | meaning |
|---|---|---|
| `master` | branch | newest development; every new feature goes here first |
| `CMSSW_<maj>_<min>_X` | branch | one release cycle; fixes only; `_X` = any patch number |
| `CMSSW_<maj>_<min>_0_pre<N>` | tag | a pre-release of a cycle still in development |
| `CMSSW_<maj>_<min>_<patch>` | tag | a release cut from the cycle branch |
| `CMSSW_<maj>_<min>_<patch>_patch<N>` | tag | a small fix on top of a release |
| `CMSSW_<maj>_<min>_X_<date>-<time>` | integration build (IB) | nightly build of a branch head |

A change goes as a pull request to `master` first. If an older cycle also
needs it, a backport PR with the same commits goes to that cycle's branch,
titled `[<maj>_<min>_X] ...`. The next release tag is cut from that branch.
Code for an older detector or data-taking period stays on such branches while
`master` moves on, because newer releases may stop supporting it.

## 3. Branch layout

| branch | role |
|---|---|
| `main` (GitHub default) | newest CMSSW cycle, all new development |
| `CMSSW_<maj>_<min>_X` | an older cycle still in use; receives ported changes and fixes |
| `feat/...`, `fix/...`, `backport/...` | short-lived, one pull request each, deleted after the merge |

- **Names follow the cycle (`_X`), not the exact release.** Pre-releases and
  patches change often; the exact release goes into a tag.
- **One clone per CMSSW area.** CMSSW needs the code under
  `CMSSW_x/src/Reco2Pico`, so each area has its own clone on the branch that
  matches its release. Check with `git branch --show-current`.
- **When an older line moves to a new cycle**, branch the new cycle from the
  old branch, port it, and freeze the old one. Its tags keep it reachable.
- **Keep the README table up to date**: which branch and CMSSW release serve
  which use case.

## 4. Tags and versions

Tag name = version + release cycle: `v<MAJOR>.<MINOR>.<PATCH>_<branch>`, e.g.
`v1.4.0_CMSSW_15_0_X`. The same version number on two branches means the same
shared features.

| part | bump when | example |
|---|---|---|
| MAJOR | the Pico format breaks analysis code (a column renamed or removed) | v1 → v2 |
| MINOR | new tables or columns | v1.3 → v1.4 |
| PATCH | bug fixes only | v1.4.0 → v1.4.1 |

- **Stamp the version in every Pico.** At submission, store
  `git describe --tags --dirty` in the file metadata or job config. `-dirty`
  marks uncommitted code; never run production with it.
- **Put the tag in the output path**, e.g. `.../reco2pico/<tag>/...`.

## 5. Porting between branches

Develop on `main`, then cherry-pick the shared commits to the release branches
that need them. Work that starts on a release branch goes forward to `main` the
same way.

- **Never `git merge` one release branch into another.** A merge takes
  everything, including release-only code; a cherry-pick takes only the
  commits you choose.
- **One topic per commit**, so a shared change never carries release-only code.
- **Keep release-specific code in few places.** Producers, tables, analysis and
  Condor tools should be identical on all branches. Eras, global tags, geometry
  and cmsDriver steps live in `PicoProducer/python/samples_workflows/<workflow>/`.
  A small Python difference can switch on `os.environ["CMSSW_VERSION"]`; a C++
  API change simply differs per branch.
- **Label pull requests** `needs-backport-<maj>_<min>_X` or `main-only`.

## 6. CI/CD

CMSSW needs `/cvmfs`, so the CI runner must mount it.

| option | how | best when |
|---|---|---|
| GitHub Actions | `cvmfs-contrib/github-action-cvmfs`, then the `cmssw/el9` container | tests need no grid or EOS inputs |
| CERN GitLab mirror | CERN runners with CVMFS, a service account for EOS | tests need EOS or grid files |

Each branch's workflow file sets its own CMSSW release. What to run, cheapest
first:

1. every push and PR: `scram b` and a load check of each config;
2. every PR: `cmsRun` on about 10 events, then compare the Pico branch list
   with a stored reference;
3. on a tag push: build, test, and create the GitHub Release;
4. optional, weekly: build `main` against the newest pre-release or IB.

## 7. Practical commands

All commands run inside a `CMSSW_x/src/Reco2Pico` checkout after `cmsenv`.

### Setting up a CMSSW area

```bash
cmsrel CMSSW_<release> && cd CMSSW_<release>/src && cmsenv
git clone -b <branch> git@github.com:theochatzis/Reco2Pico.git   # main for the newest cycle
scram b -j 8
```

### Daily work

```bash
git branch --show-current          # right branch for this area?
git pull --rebase                   # latest of this branch
git switch -c feat/my-change        # one topic per branch
git commit -m "..."; git push -u origin feat/my-change
gh pr create --base main            # or --base <branch> for work only needed there
```

### Porting a change to another branch

```bash
git fetch origin
git switch -c backport/my-change origin/<branch>
git cherry-pick -x <sha>            # conflict: fix files, git add, git cherry-pick --continue
                                    # give up:  git cherry-pick --abort
scram b -j 8                        # must build in this release
gh pr create --base <branch> --title "[<maj>_<min>_X] my change"

# commits on main not yet on <branch>
git log --oneline --no-merges --cherry-pick --right-only origin/<branch>...origin/main
```

### Making a release

```bash
git switch <branch> && git pull
git status                          # must be clean
scram b -j 8                        # and run the short cmsRun test
git tag -l 'v*_<branch>'            # last version on this branch
git tag -a <tag> -m "what changed"
git push origin <tag>
gh release create <tag> --generate-notes
```

A bug fix after a release: commit it on the branch, port it where shared,
then tag the next PATCH version.

### Using a release

```bash
git describe --tags --dirty         # which version is checked out?
git switch --detach <tag>           # reproduce an old production exactly
git switch <branch>                 # back to the branch

# stamp the version in a submission script
RECO2PICO_VERSION=$(git -C $CMSSW_BASE/src/Reco2Pico describe --tags --dirty --always)
```

### Starting a new release branch

```bash
# main moves to a new cycle: freeze the current one first
git switch -c CMSSW_<maj>_<min>_X origin/main
git push -u origin CMSSW_<maj>_<min>_X

# an older line moves to a new cycle: branch from its current branch
git switch -c CMSSW_<new>_X origin/CMSSW_<old>_X
git push -u origin CMSSW_<new>_X

# retire a branch that is fully merged or frozen and tagged
git push origin --delete <old-branch>
```
