locals {
  environment = "stg"

  api_monitors = {
    error_rate = {
      critical = 5
      warning  = 2
    }
    latency = {
      critical = 800
      warning  = 400
    }
  }

  notification_channel = "@slack-stg-alerts"
}
