$TestSuiteName = "phoenix"
$artifactsDir = "$PSScriptRoot/artifacts"

$filesCovered = @("$PSScriptRoot\providers\*.ps1")

# run pester test cases
$testOutputFile = "$artifactsDir/Pester-Results.xml"
$coverOutputFile = "$artifactsDir/Pester-Coverage.xml"

#Install-Module 'Pester' -MinimumVersion '5.3.0' -Verbose -Force
$PesterPreference = New-PesterConfiguration
$PesterPreference.Should.ErrorAction = 'Continue'
$PesterPreference.TestResult.Enabled = $true
$PesterPreference.TestResult.OutputPath = $testOutputFile
$PesterPreference.TestResult.OutputFormat = 'NUnitXml'
$PesterPreference.TestResult.TestSuiteName = $TestSuiteName
$PesterPreference.CodeCoverage.Enabled = $true
$PesterPreference.CodeCoverage.Path = $filesCovered
$PesterPreference.CodeCoverage.OutputPath = $coverOutputFile
$PesterPreference.CodeCoverage.OutputFormat = "JaCoCo"
$PesterPreference.Run.Exit = $false
$PesterPreference.Output.Verbosity = 'Detailed'

if (!(test-path -path $artifactsDir)) {new-item -path $artifactsDir -itemtype directory}

Invoke-Pester