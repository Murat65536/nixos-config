{
  config,
  pkgs,
  ...
}:

let
  user = "bob";
  homeDirectory = config.users.users.${user}.home;
  stateDirectory = "${homeDirectory}/.local/state/cync-lights";
  wakeState = "${stateDirectory}/wake.json";

  scheduler = pkgs.writeShellApplication {
    name = "cync-lights-schedule-wake";
    text = ''
      state=${wakeState}
      unit=cync-lights-wake
      ack=/run/cync-lights-wake.ack
      ack_tmp=/run/cync-lights-wake.ack.tmp

      ${pkgs.systemd}/bin/systemctl stop "$unit.timer" 2>/dev/null || true
      ${pkgs.coreutils}/bin/rm -f "$ack" "$ack_tmp"
      [[ -r "$state" ]] || exit 0

      wake_at="$(${pkgs.jq}/bin/jq -r '.wake_at // empty' "$state")"
      [[ -n "$wake_at" ]] || exit 0

      wake_epoch="$(${pkgs.coreutils}/bin/date -d "$wake_at" +%s)"
      now_epoch="$(${pkgs.coreutils}/bin/date +%s)"
      if (( wake_epoch <= now_epoch )); then
        exit 0
      fi

      calendar="$(${pkgs.coreutils}/bin/date -d "$wake_at" '+%Y-%m-%d %H:%M:%S')"

      ${pkgs.systemd}/bin/systemd-run \
        --unit="$unit" \
        --description="Wake suspended laptop for Cync room lights" \
        --on-calendar="$calendar" \
        --timer-property=WakeSystem=true \
        --timer-property=AccuracySec=1s \
        --property=Type=oneshot \
        ${pkgs.systemd}/bin/systemd-inhibit \
          --what=sleep:idle:handle-lid-switch \
          --who="cync-lights-wake" \
          --why="Turn on Cync room lights before laptop re-suspends" \
          --mode=block \
          ${pkgs.curl}/bin/curl -fsS --retry 6 --retry-delay 5 --retry-connrefused \
            -X POST -H 'Content-Type: application/json' \
            -d '{"action":"wake_if_due"}' http://127.0.0.1:8765/api/power

      ${pkgs.systemd}/bin/systemctl is-active --quiet "$unit.timer"
      printf '%s\n' "$wake_at" > "$ack_tmp"
      ${pkgs.coreutils}/bin/chmod 0644 "$ack_tmp"
      ${pkgs.coreutils}/bin/mv "$ack_tmp" "$ack"
    '';
  };
in
{
  # Stop the user bridge before Bluetooth is suspended and start it again on
  # resume. This avoids retaining a stale BlueZ GATT connection across sleep.
  systemd.services.cync-lights-suspend = {
    description = "Disconnect Cync room lights around system sleep";
    wantedBy = [ "sleep.target" ];
    before = [ "sleep.target" ];
    unitConfig.StopWhenUnneeded = true;
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      ExecStart = "${pkgs.systemd}/bin/systemctl --machine=${user}@.host --user stop cync-lights.service";
      ExecStop = "${pkgs.systemd}/bin/systemctl --machine=${user}@.host --user start cync-lights.service";
      TimeoutSec = "20s";
    };
  };

  # A system path unit mirrors the user-owned wake deadline into a privileged
  # transient timer because only the system manager can set WakeSystem=true.
  systemd.paths.cync-lights-wake-scheduler = {
    description = "Watch for Cync room-light wake deadlines";
    wantedBy = [ "multi-user.target" ];
    pathConfig = {
      PathChanged = wakeState;
      Unit = "cync-lights-wake-scheduler.service";
    };
  };

  systemd.services.cync-lights-wake-scheduler = {
    description = "Schedule the Cync room-light RTC wake";
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      ExecStart = "${scheduler}/bin/cync-lights-schedule-wake";
      UMask = "0077";
    };
  };
}
