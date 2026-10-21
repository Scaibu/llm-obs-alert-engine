{{/*
Expand the name of the chart.
*/}}
{{- define "alert-engine.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "alert-engine.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "alert-engine.labels" -}}
helm.sh/chart: {{ include "alert-engine.name" . }}-{{ .Chart.Version | replace "+" "_" }}
{{ include "alert-engine.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: llm-obs
{{- end }}

{{/*
Selector labels
*/}}
{{- define "alert-engine.selectorLabels" -}}
app.kubernetes.io/name: {{ include "alert-engine.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
