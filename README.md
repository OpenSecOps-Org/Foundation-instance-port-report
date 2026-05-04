# Instance Port Report

[![Daily CVE scan](https://github.com/OpenSecOps-Org/Foundation-instance-port-report/actions/workflows/daily-scan.yml/badge.svg)](https://github.com/OpenSecOps-Org/Foundation-instance-port-report/actions/workflows/daily-scan.yml) [![OpenSSF Scorecard](https://github.com/OpenSecOps-Org/Foundation-instance-port-report/actions/workflows/scorecard.yml/badge.svg)](https://github.com/OpenSecOps-Org/Foundation-instance-port-report/actions/workflows/scorecard.yml)

## Deployment

First make sure that your SSO setup is configured with a default profile giving you AWSAdministratorAccess
to your AWS Organizations administrative account. This is necessary as the AWS cross-account role used 
during deployment only can be assumed from that account.

```console
aws sso login
```

Then type:

```console
./deploy
```
