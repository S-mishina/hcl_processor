# Multiple monitors for chunk processing test

module "datadog_monitors" {
  source = "../modules/monitor"

  monitors = [
    {
      name    = "CPU High Alert"
      type    = "query alert"
      message = "CPU usage is too high. @slack-alerts"
      query   = "avg(last_5m):avg:system.cpu.user{*} > 80"
      thresholds = {
        critical = 80
        warning  = 60
      }
    },
    {
      name    = "Memory High Alert"
      type    = "query alert"
      message = "Memory usage is too high. @slack-alerts"
      query   = "avg(last_5m):avg:system.mem.used{*} / avg:system.mem.total{*} * 100 > 90"
      thresholds = {
        critical = 90
        warning  = 80
      }
    },
    {
      name    = "Disk Usage Alert"
      type    = "query alert"
      message = "Disk usage is too high. @slack-alerts"
      query   = "avg(last_5m):avg:system.disk.in_use{*} * 100 > 85"
      thresholds = {
        critical = 85
        warning  = 70
      }
    },
    {
      name    = "Network Errors Alert"
      type    = "query alert"
      message = "Network errors detected. @slack-alerts"
      query   = "sum(last_5m):sum:system.net.errors{*}.as_count() > 100"
      thresholds = {
        critical = 100
        warning  = 50
      }
    },
    {
      name    = "API Error Rate v2"
      type    = "query alert"
      message = "API error rate is elevated. @slack-api-alerts"
      query   = "sum(last_5m):sum:trace.servlet.request.errors{service:api-gateway}.as_count() / sum:trace.servlet.request.hits{service:api-gateway}.as_count() * 100 > 5"
      thresholds = {
        critical = 5
        warning  = 2
      }
    },
    {
      name    = "Database Connections Alert"
      type    = "query alert"
      message = "Database connections are reaching the limit. @slack-db-alerts"
      query   = "avg(last_5m):avg:postgresql.connections{*} > 80"
      thresholds = {
        critical = 80
        warning  = 60
      }
    },
    {
      name    = "Redis Memory Alert"
      type    = "query alert"
      message = "Redis memory usage is high. @slack-cache-alerts"
      query   = "avg(last_5m):avg:redis.mem.used{*} / avg:redis.mem.maxmemory{*} * 100 > 75"
      thresholds = {
        critical = 75
        warning  = 60
      }
    },
    {
      name    = "Kafka Consumer Lag Alert"
      type    = "query alert"
      message = "Kafka consumer lag is too high. @slack-kafka-alerts"
      query   = "avg(last_5m):avg:kafka.consumer.lag{*} > 10000"
      thresholds = {
        critical = 10000
        warning  = 5000
      }
    },
    {
      name    = "Elasticsearch Cluster Health"
      type    = "query alert"
      message = "Elasticsearch cluster health is degraded. @slack-search-alerts"
      query   = "avg(last_5m):avg:elasticsearch.cluster_status{*} > 1"
      thresholds = {
        critical = 2
        warning  = 1
      }
    },
    {
      name    = "RabbitMQ Queue Depth Alert"
      type    = "query alert"
      message = "RabbitMQ queue depth is high. @slack-mq-alerts"
      query   = "avg(last_5m):avg:rabbitmq.queue.messages{*} > 5000"
      thresholds = {
        critical = 5000
        warning  = 2000
      }
    },
    {
      name    = "Load Balancer 5xx Errors"
      type    = "query alert"
      message = "High 5xx error rate on load balancer. @slack-infra-alerts @pagerduty-oncall"
      query   = "sum(last_5m):sum:aws.elb.httpcode_elb_5xx{*}.as_count() > 50"
      thresholds = {
        critical = 50
        warning  = 20
      }
    },
    {
      name    = "Container CPU Throttling"
      type    = "query alert"
      message = "Container CPU throttling detected. @slack-k8s-alerts"
      query   = "avg(last_5m):avg:kubernetes.cpu.throttled{*} by {container_name} > 0.5"
      thresholds = {
        critical = 0.5
        warning  = 0.3
      }
    },
    {
      name    = "Pod Restart Rate Alert"
      type    = "query alert"
      message = "Pod restart rate is elevated. @slack-k8s-alerts"
      query   = "sum(last_15m):sum:kubernetes_state.container.restarts{*} by {pod_name}.as_count() > 5"
      thresholds = {
        critical = 5
        warning  = 3
      }
    },
    {
      name    = "SSL Certificate Expiry"
      type    = "service check"
      message = "SSL certificate is expiring soon. @slack-security-alerts"
      query   = "ssl.cert.remaining_days{*} < 14"
      thresholds = {
        critical = 7
        warning  = 14
      }
    },
    {
      name    = "DNS Resolution Latency"
      type    = "query alert"
      message = "DNS resolution latency is high. @slack-network-alerts"
      query   = "avg(last_5m):avg:network.dns.response_time{*} > 100"
      thresholds = {
        critical = 100
        warning  = 50
      }
    },
    {
      name    = "MongoDB Replication Lag"
      type    = "query alert"
      message = "MongoDB replication lag is too high. @slack-db-alerts"
      query   = "avg(last_5m):avg:mongodb.replset.replicationlag{*} > 60"
      thresholds = {
        critical = 60
        warning  = 30
      }
    },
    {
      name    = "Lambda Function Errors"
      type    = "query alert"
      message = "AWS Lambda function errors detected. @slack-serverless-alerts"
      query   = "sum(last_5m):sum:aws.lambda.errors{*} by {functionname}.as_count() > 10"
      thresholds = {
        critical = 10
        warning  = 5
      }
    },
    {
      name    = "SQS Dead Letter Queue"
      type    = "query alert"
      message = "Messages in Dead Letter Queue. @slack-async-alerts @pagerduty-oncall"
      query   = "avg(last_5m):avg:aws.sqs.approximate_number_of_messages_visible{queuename:*-dlq} > 0"
      thresholds = {
        critical = 10
        warning  = 1
      }
    },
    {
      name    = "EC2 Instance Status Check"
      type    = "service check"
      message = "EC2 instance status check failed. @slack-infra-alerts @pagerduty-oncall"
      query   = "aws.ec2.status_check_failed_system{*}"
      thresholds = {
        critical = 1
        warning  = 0
      }
    },
    {
      name    = "S3 Bucket Request Latency"
      type    = "query alert"
      message = "S3 bucket request latency is high. @slack-storage-alerts"
      query   = "avg(last_5m):avg:aws.s3.total_request_latency{*} by {bucketname} > 200"
      thresholds = {
        critical = 200
        warning  = 100
      }
    },
    {
      name    = "CloudFront Error Rate"
      type    = "query alert"
      message = "CloudFront error rate is elevated. @slack-cdn-alerts"
      query   = "sum(last_5m):sum:aws.cloudfront.5xx_error_rate{*}.as_count() / sum:aws.cloudfront.requests{*}.as_count() * 100 > 5"
      thresholds = {
        critical = 5
        warning  = 2
      }
    },
    {
      name    = "ECS Task Memory Utilization"
      type    = "query alert"
      message = "ECS task memory utilization is high. @slack-ecs-alerts"
      query   = "avg(last_5m):avg:ecs.task.memory.utilized{*} by {task_family} / avg:ecs.task.memory.reserved{*} by {task_family} * 100 > 90"
      thresholds = {
        critical = 90
        warning  = 80
      }
    },
    {
      name    = "RDS Connection Count"
      type    = "query alert"
      message = "RDS database connection count is high. @slack-db-alerts"
      query   = "avg(last_5m):avg:aws.rds.database_connections{*} by {dbinstanceidentifier} > 100"
      thresholds = {
        critical = 100
        warning  = 80
      }
    },
    {
      name    = "DynamoDB Throttled Requests"
      type    = "query alert"
      message = "DynamoDB throttled requests detected. @slack-db-alerts"
      query   = "sum(last_5m):sum:aws.dynamodb.throttled_requests{*} by {tablename}.as_count() > 10"
      thresholds = {
        critical = 10
        warning  = 5
      }
    },
    {
      name    = "Application Log Errors"
      type    = "log alert"
      message = "High number of application errors in logs. @slack-app-alerts"
      query   = "logs(\"status:error service:backend\").index(\"main\").rollup(\"count\").last(\"5m\") > 100"
      thresholds = {
        critical = 100
        warning  = 50
      }
    },
    {
      name    = "Nginx Request Rate"
      type    = "query alert"
      message = "Nginx request rate spike detected. @slack-web-alerts"
      query   = "avg(last_5m):avg:nginx.requests.total_count{*}.as_rate() > 10000"
      thresholds = {
        critical = 10000
        warning  = 5000
      }
    },
    {
      name    = "JVM Heap Memory Usage"
      type    = "query alert"
      message = "JVM heap memory usage is high. @slack-java-alerts"
      query   = "avg(last_5m):avg:jvm.heap_memory{*} by {instance} / avg:jvm.heap_memory_max{*} by {instance} * 100 > 85"
      thresholds = {
        critical = 85
        warning  = 75
      }
    }
  ]

  environment = var.environment
  tags        = var.tags
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "tags" {
  type        = list(string)
  description = "Tags to apply"
  default     = ["managed:terraform"]
}
