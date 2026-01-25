locals {
  environment = "prd"

  api_monitors = {
    error_rate = {
      critical = 1
      warning  = 0.5
    }
    latency = {
      critical = 500
      warning  = 200
    }
  }

  notification_channel = "@slack-prd-alerts @pagerduty-oncall"
}
