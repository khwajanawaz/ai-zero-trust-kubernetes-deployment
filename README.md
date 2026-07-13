# AI-Driven Zero-Trust Kubernetes Deployment Framework

An intelligent deployment gateway that validates Kubernetes manifests using Open Policy Agent (OPA), AI-powered risk analysis, Temporal workflows, and human approval before securely deploying workloads to Amazon EKS.

![Python](https://img.shields.io/badge/Python-3.11-blue)

![FastAPI](https://img.shields.io/badge/FastAPI-API-green)

![Docker](https://img.shields.io/badge/Docker-Containers-blue)

![Kubernetes](https://img.shields.io/badge/Kubernetes-EKS-326CE5)

![OPA](https://img.shields.io/badge/OpenPolicyAgent-Policy-purple)

![Temporal](https://img.shields.io/badge/Temporal-Workflow-orange)

![AWS](https://img.shields.io/badge/AWS-EKS-yellow)

![MIT License](https://img.shields.io/badge/License-MIT-green)

## Overview

Traditional Kubernetes deployments mainly validate YAML syntax before deployment.

However, syntax validation alone cannot detect security risks such as:

- latest image tags
- missing resource limits
- privileged containers
- insecure networking
- policy violations

This project introduces an AI-powered Zero-Trust deployment gateway that performs multiple validation stages before allowing any workload to reach an Amazon EKS cluster.

The framework combines:

- FastAPI
- Temporal Workflows
- Open Policy Agent (OPA)
- OpenAI Risk Analysis
- Human Approval
- Amazon Elastic Kubernetes Service (EKS)

Only workloads that successfully pass every validation stage are deployed.













User sends YAML to FastAPI MCP server
↓
MCP server validates YAML
↓
MCP server starts a Temporal workflow
↓
Temporal workflow runs these steps:
   1. validate manifest
   2. fetch cluster context
   3. call AI analysis
   4. call OPA policy check
   5. combine result
   6. wait for human approval
   7. if approved → apply manifest to cluster
↓
MCP API returns workflow id
↓
User later approves or denies using API
↓
Workflow continues and finishes

