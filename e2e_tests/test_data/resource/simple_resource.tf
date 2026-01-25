# Simple resource pattern test (not using module)

resource "datadog_monitor" "http_check" {
  name    = "HTTP Health Check - ${var.environment}"
  type    = "service check"
  message = <<-EOF
    HTTP endpoint is not responding.
    @slack-oncall
  EOF

  query = "\"http.can_connect\".over(\"instance:production\").by(\"host\",\"instance\",\"url\").last(3).count_by_status()"

  tags = ["service:http-check", "env:${var.environment}"]
}

resource "datadog_monitor" "process_check" {
  name    = "Process Check - nginx"
  type    = "process alert"
  message = <<-EOF
    nginx process is not running.
    @pagerduty-oncall
  EOF

  query = "processes('nginx').over('*').rollup('count').last('5m') < 1"

  tags = ["service:nginx", "team:infra"]
}

resource "datadog_monitor" "log_anomaly" {
  name    = "Log Anomaly Detection"
  type    = "log alert"
  message = <<-EOF
    Unusual log patterns detected.
    @slack-security
  EOF

  query = "logs(\"status:error service:auth\").index(\"main\").rollup(\"count\").last(\"15m\") > 100"

  tags = ["service:auth", "team:security"]
}

variable "environment" {
  type    = string
  default = "production"
}
