pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install dependencies') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"

                    if (Test-Path 'ci-reports') {
                        Remove-Item 'ci-reports' -Recurse -Force
                    }

                    New-Item -ItemType Directory -Path 'ci-reports' |
                        Out-Null

                    python -m venv --clear .ci-venv
                    if ($LASTEXITCODE -ne 0) {
                        throw "Failed to create virtual environment"
                    }

                    $python = Join-Path $env:WORKSPACE '.ci-venv/Scripts/python.exe'

                    & $python -m pip install -r requirements-dev.txt
                    if ($LASTEXITCODE -ne 0) {
                        throw "Dependency installation failed"
                    }

                    & $python -m pip freeze |
                        Out-File 'ci-reports/installed-packages.txt'
                '''
            }
        }

        stage('Static analysis - Bandit') {
            steps {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        $bandit = Join-Path $env:WORKSPACE '.ci-venv/Scripts/bandit.exe'

                        & $bandit -r application_api resource_service processing_service textstats-lib/textstats_lib -f json -o ci-reports/bandit.json

                        $scanExit = $LASTEXITCODE

                        if ($scanExit -gt 1 -or -not (Test-Path 'ci-reports/bandit.json')) {
                            throw "Bandit scan failed"
                        }

                        $report = Get-Content 'ci-reports/bandit.json' -Raw |
                            ConvertFrom-Json

                        $findings = @($report.results | Where-Object { $null -ne $_ })

                        $blocking = @($report.results | Where-Object {
                            $null -ne $_ -and
                            $_.issue_severity -eq 'HIGH' -and
                            $_.issue_confidence -in @('MEDIUM', 'HIGH')
                        })

                        Write-Host "Bandit findings: $($findings.Count)"
                        Write-Host "Release-blocking findings: $($blocking.Count)"

                        if ($blocking.Count -gt 0) {
                            throw "Bandit release gate failed"
                        }
                    '''
                }
            }
        }

        stage('Dependency analysis - pip-audit') {
            steps {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        $python = Join-Path $env:WORKSPACE '.ci-venv/Scripts/python.exe'

                        & $python -m pip_audit --local --format json --output ci-reports/pip-audit.json

                        if ($LASTEXITCODE -ne 0) {
                            throw "Dependency audit failed: vulnerabilities or scan error"
                        }
                    '''
                }
            }
        }

        stage('Functional and security tests') {
            steps {
                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        $python = Join-Path $env:WORKSPACE '.ci-venv/Scripts/python.exe'

                        & $python ci/run_tests.py

                        if ($LASTEXITCODE -ne 0) {
                            throw "Functional or security tests failed"
                        }
                    '''
                }
            }
        }
    }

    post {
        always {
            junit testResults: 'ci-reports/*.xml',
                  allowEmptyResults: true

            archiveArtifacts artifacts: 'ci-reports/**',
                             allowEmptyArchive: true
        }
    }
}
