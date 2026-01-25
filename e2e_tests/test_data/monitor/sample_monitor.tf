resource "datadog_monitor" "api_error_rate" {
  name    = "API Error Rate Monitor - ${var.environment}"
  type    = "query alert"
  message = <<-EOF
    API error rate is too high.
    @slack-alerts-channel
  EOF

  query = "sum(last_5m):sum:api.errors{service:backend}.as_count() / sum:api.requests{service:backend}.as_count() * 100 > ${local.api_monitors.error_rate.critical}"

  monitor_thresholds {
    critical = local.api_monitors.error_rate.critical
    warning  = local.api_monitors.error_rate.warning
  }

  tags = ["service:backend", "team:platform", "env:${var.environment}"]
}

resource "datadog_monitor" "api_latency" {
  name    = "API Latency Monitor - ${var.environment}"
  type    = "query alert"
  message = <<-EOF
    API latency is too high.
    @slack-alerts-channel
  EOF

  query = "avg(last_5m):avg:api.latency{service:backend} > ${local.api_monitors.latency.critical}"

  monitor_thresholds {
    critical = local.api_monitors.latency.critical
    warning  = local.api_monitors.latency.warning
  }

  tags = ["service:backend", "team:platform", "env:${var.environment}"]
}
