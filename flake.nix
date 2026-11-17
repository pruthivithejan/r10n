{
  description = "r10n development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      forAllSystems = function:
        nixpkgs.lib.genAttrs systems (system: function nixpkgs.legacyPackages.${system});
    in {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            go
            python312
            uv
            lefthook
            git
          ];

          shellHook = ''
            echo "r10n dev shell"
            echo "  go      $(go version | cut -d' ' -f3)"
            echo "  python  $(python --version 2>&1 | cut -d' ' -f2)"
            echo "  uv      $(uv --version)"
            echo "Run ./setup.sh setup to sync modules and install hooks."
          '';
        };
      });

      formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);
    };
}
