{
  cliProxyApi,
  cyncLights,
  ...
}:

{
  systemd.user.services = {
    cli-proxy-api = {
      Unit = {
        Description = "CLIProxyAPI local inference proxy for Hermes";
        ConditionPathExists = "%h/.config/cli-proxy-api/config.yaml";
      };
      Service = {
        Type = "simple";
        ExecStart = "${cliProxyApi}/bin/cli-proxy-api -config %h/.config/cli-proxy-api/config.yaml";
        Restart = "on-failure";
        RestartSec = "3s";
      };
      Install.WantedBy = [ "default.target" ];
    };

    cync-lights = {
      Unit = {
        Description = "Cync room lights bridge for Dank Material Shell";
        PartOf = [ "graphical-session.target" ];
        After = [ "graphical-session.target" ];
        ConditionPathExists = "%h/.local/state/cync-lights/mesh.json";
      };
      Service = {
        Type = "simple";
        ExecStart = "${cyncLights}/bin/cync-lights";
        Restart = "on-failure";
        RestartSec = "5s";
        TimeoutStopSec = "15s";
      };
      Install.WantedBy = [ "graphical-session.target" ];
    };
  };
}
