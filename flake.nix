{
  description = "Silverpond Factory CLI";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;

        silverpond-factory = python.pkgs.buildPythonPackage {
          pname = "silverpond-factory";
          version = "0.1.0";
          src = ./.;
          pyproject = true;

          build-system = with python.pkgs; [ setuptools ];

          dependencies = with python.pkgs; [
            typer
            rich
            pydantic
            pyyaml
            questionary
            slack-sdk
          ];
        };
      in {
        packages.default = silverpond-factory;

        apps.default = {
          type = "app";
          program = "${silverpond-factory}/bin/factory";
        };

        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: with ps; [
              typer rich pydantic pyyaml questionary slack-sdk
            ]))
          ];
        };
      }
    );
}
