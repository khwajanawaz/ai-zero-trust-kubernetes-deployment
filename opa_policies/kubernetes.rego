package kubernetes.admission

default allow := false

violations contains msg if {
  container := input.spec.template.spec.containers[_]
  endswith(container.image, ":latest")
  msg := "latest image tag is not allowed"
}

violations contains msg if {
  container := input.spec.template.spec.containers[_]
  not container.resources.limits
  msg := "resource limits are required"
}

allow if {
  count(violations) == 0
}