pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify environment') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"

                    git --version
                    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

                    python --version
                    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

                    python -m pip --version
                    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

                    Write-Host "Job: $env:JOB_NAME"
                    Write-Host "Branch: $env:BRANCH_NAME"
                '''
            }
        }
    }
}
