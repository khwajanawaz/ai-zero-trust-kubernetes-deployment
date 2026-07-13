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

## Features

- Zero Trust Deployment Pipeline
- Kubernetes YAML Validation
- Open Policy Agent Policy Enforcement
- AI Security Risk Analysis
- Human Approval Workflow
- Amazon EKS Deployment
- Dockerized Services
- Temporal Workflow Orchestration
- REST API
- Policy-based Deployment Decisions
- Audit Logging
- Containerized Architecture


  ## Deployment Workflow

1. Developer submits Kubernetes YAML.
2. FastAPI receives the request.
3. Temporal starts a deployment workflow.
4. OPA validates security policies.
5. OpenAI analyzes deployment risks.
6. Human approval is requested if required.
7. Deployment proceeds only after successful validation.
8. Kubernetes deploys the workload into Amazon EKS.


## 🏗️ System Architecture

The overall architecture of the AI-Driven Zero-Trust Kubernetes Deployment Framework.

<p align="center">
  <img src="docs/images/architecture.png" width="700">
</p>

## 📚 Swagger API Documentation

The project exposes REST APIs for Kubernetes deployment validation and approval.

<p align="center">
  <img src="docs/images/swaggerhome.png" width="1000">
</p>

## 🚀 Submit Kubernetes Manifest

Developers submit a Kubernetes deployment manifest through the FastAPI endpoint.

<p align="center">
  <img src="docs/images/submit-yaml.png" width="1000">
</p>

## ⚙️ Workflow Started

A new Temporal workflow is automatically created after receiving the deployment request.

<p align="center">
  <img src="docs/images/workflow-running.png" width="1000">
</p>

## ⏳ Waiting for Human Approval

The workflow pauses until an administrator reviews and approves the deployment.

<p align="center">
  <img src="docs/images/waiting-approval.png" width="1000">
</p>

## ✅ Deployment Approval

The administrator approves the deployment through the Approval API.

<p align="center">
  <img src="docs/images/approval-api.png" width="1000">
</p>

## 🎉 Workflow Completed

After approval, the deployment workflow completes successfully.

<p align="center">
  <img src="docs/images/workflow-completed.png" width="1000">
</p>

## 📈 Temporal Workflow Timeline

Temporal provides a complete execution timeline for every deployment.

<p align="center">
  <img src="docs/images/temporal-timeline.png" width="1000">
</p>

## ☁️ Deployment Result

The deployment has been successfully applied to Amazon EKS.

<p align="center">
  <img src="docs/images/deployment-result.png" width="1000">
</p>


## 🚀 Running on Amazon EKS

The deployed application is successfully running in the Kubernetes cluster.

<p align="center">
  <img src="docs/images/kubectl-pods.png" width="1000">
</p>










Workflow continues and finishes

