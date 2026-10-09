{ config, lib, pkgs, ... }:
let
  cfg = config.programs.ctxVoice;
  package = pkgs.callPackage ./package.nix {};
in {
  options.programs.ctxVoice = {
    enable = lib.mkEnableOption "opt-in Context Switcher voice extension";
    package = lib.mkOption {
      type = lib.types.package;
      default = package;
      description = "Voice CLI package. No microphone background service.";
    };
  };
  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ cfg.package ];
  };
}
