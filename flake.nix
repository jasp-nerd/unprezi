{
  description = "Export a prezi.com presentation to a PDF.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;

        unprezi = python.pkgs.buildPythonApplication {
          pname = "unprezi";
          version = "0.1.2";
          pyproject = true;

          src = ./.;

          nativeBuildInputs = with python.pkgs; [
            hatchling
          ];

          propagatedBuildInputs = with python.pkgs; [
            playwright
            img2pdf
            pillow
          ];

          makeWrapperArgs = [
            "--set PLAYWRIGHT_BROWSERS_PATH ${pkgs.playwright-driver.browsers}"
          ];

          meta = with pkgs.lib; {
            description = "Export a prezi.com presentation to a PDF.";
            homepage = "https://github.com/jasp-nerd/unprezi";
            license = licenses.mit;
            mainProgram = "unprezi";
          };
        };
      in
      {
        packages = {
          default = unprezi;
          unprezi = unprezi;
        };

        apps = {
          default = flake-utils.lib.mkApp {
            drv = unprezi;
          };
          unprezi = flake-utils.lib.mkApp {
            drv = unprezi;
          };
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ unprezi ];
          packages = with python.pkgs; [
            pkgs.playwright-driver.browsers
          ];
          shellHook = ''
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
          '';
        };
      });
}
