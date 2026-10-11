{
  description = "Standalone Material You theme generator with caelestia-exact colour extraction";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
    ...
  }:
    let
      systems = [ "x86_64-linux" ];

      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system:
          f {
            inherit system;
            pkgs = import nixpkgs { inherit system; };
          });
    in
    {
      packages = forAllSystems ({ pkgs, ... }: rec {
        morphism-gen = pkgs.callPackage ./default.nix { };
        default = morphism-gen;
      });

      apps = forAllSystems ({ system, ... }: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/morphism-gen";
          meta.description = "Run morphism-gen";
        };
      });

      devShells = forAllSystems ({ pkgs, ... }: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: [
              ps.materialyoucolor
              ps.pillow
            ]))
            pkgs.nixfmt
          ];
        };
      });

      checks = forAllSystems ({ pkgs, ... }: {
        default = pkgs.runCommand "morphism-gen-checks" {
          nativeBuildInputs = [
            (pkgs.python3.withPackages (ps: [
              ps.materialyoucolor
              ps.pillow
            ]))
          ];
        } ''
          cp -r ${self}/src ./src
          cp -r ${self}/tests ./tests
          chmod -R u+w src tests
          cd tests
          python -m unittest discover -s . -t . -v
          touch $out
        '';
      });

      formatter = forAllSystems ({ pkgs, ... }: pkgs.nixfmt);
    };
}
