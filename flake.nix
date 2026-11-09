{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
    }@inputs:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python3;

      htpy = python.pkgs.buildPythonPackage rec {
        pname = "htpy";
        version = "26.5.1";
        pyproject = true;

        src = pkgs.fetchPypi {
          inherit pname version;
          hash = "sha256-Q6NlwfxnAJTaeBuSOIMBkznOwDE5fWHV/l+OLyJ4tj4=";
        };

        build-system = [
          python.pkgs.setuptools
          python.pkgs.setuptools-scm
        ];
        dependencies = [ python.pkgs.markupsafe ];

        pythonImportsCheck = [ "htpy" ];
        doCheck = false;
      };

      pythonForBuildingPages = python.withPackages (packages: [ htpy ]);

      deploy = pkgs.writeShellApplication {
        name = "deploy";
        runtimeInputs = [
          pythonForBuildingPages
          pkgs.mpremote
        ];
        text = builtins.readFile ./deploy.sh;
      };
      push-sequences = pkgs.writeShellApplication {
        name = "push-sequences";
        runtimeInputs = [ pythonForBuildingPages pkgs.curl ];
        text = builtins.readFile ./push_sequences.sh;
      };
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          pythonForBuildingPages
          pkgs.mpremote
          python.pkgs.httpx
          deploy
          push-sequences
        ];
      };
    };
}
