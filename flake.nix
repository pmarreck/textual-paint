{
  description = "Textual Paint - A TUI image viewer and editor";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;

        # Core dependencies
        corePythonPackages = ps: with ps; [
          pillow
          pyfiglet
          pyperclip
          pyxdg
          rich
          stransi
          textual
          pip # Include pip for optional dependencies
        ];

        # Development dependencies
        devPythonPackages = ps: with ps; [
          textual-dev
          watchdog
          types-pillow
          types-psutil
          pytest
          pytest-asyncio
          pytest-textual-snapshot
          pyfakefs
          build
          twine
        ];

        # System-specific packages
        darwinPackages = pkgs.lib.optionals pkgs.stdenv.isDarwin [
          pkgs.darwin.apple_sdk.frameworks.Cocoa
        ];

      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            (python.withPackages (ps: corePythonPackages ps ++ devPythonPackages ps))
            pkgs.pyright
          ] ++ darwinPackages;

          shellHook = ''
            echo "Textual Paint development environment activated!"
            ${if pkgs.stdenv.isDarwin then ''
              # Install optional macOS-specific packages if not present
              python -m pip install --user "appscript==1.2.2" "pyobjc-framework-Quartz==9.2" 2>/dev/null || true
            '' else ""}

            # Set PYTHONPATH to include user site-packages
            export PYTHONPATH="$HOME/.local/lib/python3.11/site-packages:$PYTHONPATH"
          '';
        };

        packages.default = python.pkgs.buildPythonPackage {
          pname = "textual-paint";
          version = "0.1.0";  # Update this as needed
          format = "setuptools";

          src = ./.;

          propagatedBuildInputs = corePythonPackages python.pkgs;

          doCheck = true;
          checkInputs = devPythonPackages python.pkgs;

          meta = with pkgs.lib; {
            description = "A TUI image viewer and editor built with Textual";
            homepage = "https://github.com/pmarreck/textual-paint";
            license = licenses.mit;  # Update if license is different
            maintainers = [ ];
          };
        };
      });
}
