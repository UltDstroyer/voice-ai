{
  description = "ctx-voice: standalone local voice extension for Context Switcher";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      perSystem = f: nixpkgs.lib.genAttrs systems
        (system: f (import nixpkgs { inherit system; }));
    in {
      packages = perSystem (pkgs: {
        default = pkgs.callPackage ./nix/package.nix {};
      });
      nixosModules.default = import ./nix/module.nix;
      nixosModules.ctx-voice = self.nixosModules.default;
      apps = nixpkgs.lib.genAttrs systems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/ctx-ext-voice";
        };
      });
    };
}
