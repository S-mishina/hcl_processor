locals {
  environment = "dev"

  api_monitors = {
    error_rate = {
      critical = 10
      warning  = 5
    }
    latency = {
      critical = 1000
      warning  = 500
    }
  }

  notification_channel = "@slack-dev-alerts"
}
