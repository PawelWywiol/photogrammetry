.DEFAULT_GOAL := help
PG := ./bin/pg

# `make my-object preview` reaches make as two goals. Treat the first as the project name,
# the second as the action, the rest as arguments — and let every goal after the first do
# nothing, so the pipeline runs exactly once.
PROJECT := $(firstword $(MAKECMDGOALS))
ACTION  := $(word 2,$(MAKECMDGOALS))
ARGS    := $(wordlist 3,99,$(MAKECMDGOALS))

.PHONY: help setup doctor list clean-build FORCE
FORCE:

# Stop the catch-all rule below from trying to "rebuild" the makefile itself.
Makefile: ;

help:
	@echo "Photogrammetry -> 3D print"
	@echo ""
	@echo "  make <project>              full run: check + reconstruct + STL   (best quality)"
	@echo "  make <project> preview      fast, rough run to see if the photos are usable"
	@echo "  make <project> check        audit the photos before spending time reconstructing"
	@echo "  make <project> build        reconstruct only, no STL"
	@echo "  make <project> stl          re-export the STL only"
	@echo "  make <project> view         render preview images of the mesh"
	@echo "  make <project> video FILE   extract photos from a video file"
	@echo "  make <project> clean        delete generated files, keep the photos"
	@echo ""
	@echo "  make setup                  install and check everything you need (run once)"
	@echo "  make doctor                 check that all requirements are present"
	@echo "  make list                   list your projects"
	@echo ""
	@echo "Example:"
	@echo "  1. put photos in projects/my-object/images/"
	@echo "  2. make my-object"
	@echo "  3. the result is projects/my-object/output/my-object.stl"
	@echo ""
	@echo "Scanning a person or a pet? Read docs/07-moving-subjects.md first."

setup:
	@command -v brew   >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
	@command -v uv     >/dev/null || brew install uv
	@command -v ffmpeg >/dev/null || brew install ffmpeg
	@xcode-select -p   >/dev/null 2>&1 || xcode-select --install
	@$(MAKE) --no-print-directory doctor

doctor:
	@echo "macOS      $$(sw_vers -productVersion) on $$(uname -m)"
	@command -v swift  >/dev/null && echo "swift      $$(swift --version 2>/dev/null | head -1)" \
	                              || echo "swift      MISSING -> xcode-select --install"
	@command -v uv     >/dev/null && echo "uv         $$(uv --version)"  || echo "uv         MISSING -> brew install uv"
	@command -v ffmpeg >/dev/null && echo "ffmpeg     present"           || echo "ffmpeg     MISSING -> brew install ffmpeg (only needed for video)"
	@test -x tools/objcap/.build/release/objcap \
	    && echo "objcap     built" \
	    || echo "objcap     not built yet (built automatically on first run)"

list:
	@ls -1 projects 2>/dev/null | grep -v '^README.md$$' || echo "(no projects yet)"

clean-build:
	@rm -rf tools/objcap/.build
	@echo "removed the compiled objcap binary"

# Anything else is a project name, optionally followed by an action.
%: FORCE
	@test "$@" = "$(PROJECT)" || exit 0; \
	case "$(ACTION)" in \
	  "")        $(PG) all   "$(PROJECT)" --detail full ;; \
	  preview)   $(PG) build "$(PROJECT)" --detail preview && $(PG) stl "$(PROJECT)" ;; \
	  check)     $(PG) check "$(PROJECT)" ;; \
	  build)     $(PG) build "$(PROJECT)" --detail full ;; \
	  stl)       $(PG) stl   "$(PROJECT)" ;; \
	  view)      $(PG) view  "$(PROJECT)" ;; \
	  video)     test -n "$(ARGS)" || { echo "usage: make $(PROJECT) video path/to/clip.mov"; exit 1; }; \
	             $(PG) frames "$(PROJECT)" $(ARGS) ;; \
	  clean)     rm -rf "projects/$(PROJECT)/output" "projects/$(PROJECT)/.prepared" "projects/$(PROJECT)/.checkpoint"; \
	             echo "cleaned projects/$(PROJECT) (photos kept)" ;; \
	  *)         echo "unknown action: $(ACTION)"; echo "try: preview check build stl view video clean"; exit 1 ;; \
	esac
