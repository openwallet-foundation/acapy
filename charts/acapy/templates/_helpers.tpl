{{/*
Expand the name of the chart.
*/}}
{{- define "acapy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create URL based on hostname and TLS status
*/}}
{{- define "acapy.agent.url" -}}
{{- if .Values.ingress.agent.tls -}}
{{- printf "https://%s" (include "acapy.host" .) }}
{{- else -}}
{{- printf "http://%s" (include "acapy.host" .) }}
{{- end -}}
{{- end }}

{{/*
Create Websockets URL based on hostname and TLS status
*/}}
{{- define "acapy.agent.wsUrl" -}}
{{- if .Values.ingress.agent.tls -}}
{{- printf "wss://%s" (include "acapy.host" .) }}
{{- else -}}
{{- printf "ws://%s" (include "acapy.host" .) }}
{{- end -}}
{{- end }}

{{/*
generate hosts if not overriden
*/}}
{{- define "acapy.host" -}}
{{- if .Values.ingress.agent.enabled -}}
    {{ .Values.ingress.agent.hostname }}
{{- else -}}
    {{ .Values.agentUrl }}
{{- end -}}
{{- end -}}

{{/*
Returns a secret if it already in Kubernetes, otherwise it creates
it randomly.

Usage:
{{ include "getOrGeneratePass" (dict "Namespace" .Release.Namespace "Kind" "Secret" "Name" (include "acapy.databaseSecretName" .) "Key" "postgres-password" "Length" 32) }}

*/}}
{{- define "getOrGeneratePass" }}
{{- $len := (default 16 .Length) | int -}}
{{- $obj := (lookup "v1" .Kind .Namespace .Name).data -}}
{{- if $obj }}
{{- index $obj .Key -}}
{{- else if (eq (lower .Kind) "secret") -}}
{{- randAlphaNum $len | b64enc -}}
{{- else -}}
{{- randAlphaNum $len -}}
{{- end -}}
{{- end }}

{{/*
Create a default fully qualified postgresql name.
*/}}
{{- define "acapy.database.secretName" -}}
{{- if .Values.walletStorageCredentials.existingSecret -}}
{{- .Values.walletStorageCredentials.existingSecret -}}
{{- else -}}
{{ printf "%s-postgresql" (include "common.names.fullname" .) }}
{{- end -}}
{{- end -}}

{{/*
Create a default fully qualified app name for the postgres requirement.
*/}}
{{- define "global.postgresql.fullname" -}}
{{- if .Values.postgresql.fullnameOverride }}
{{- .Values.postgresql.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $postgresContext := dict "Values" .Values.postgresql "Release" .Release "Chart" (dict "Name" "postgresql") -}}
{{ template "postgresql.v1.primary.fullname" $postgresContext }}
{{- end -}}
{{- end -}}

{{/*
Generate acapy wallet storage config
*/}}
{{- define "acapy.walletStorageConfig" -}}
{{- if .Values.walletStorageConfig.json -}}
    {{- .Values.walletStorageConfig.json -}}
{{- else if .Values.walletStorageConfig.url -}}
    '{"url":"{{ .Values.walletStorageConfig.url }}","max_connections":"{{ .Values.walletStorageConfig.max_connection | default 10 }}", "wallet_scheme":"{{ .Values.walletStorageConfig.wallet_scheme }}"}'
{{- else if .Values.postgresql.enabled -}}
    '{"url":"{{ include "global.postgresql.fullname" . }}:{{ .Values.postgresql.primary.service.ports.postgresql }}","max_connections":"{{ .Values.walletStorageConfig.max_connections }}","wallet_scheme":"{{ .Values.walletStorageConfig.wallet_scheme }}"}'
{{- else -}}
    ''
{{ end }}
{{- end -}}

{{/*
Generate acapy wallet storage credentials
*/}}
{{- define "acapy.walletStorageCredentials" -}}
{{- if .Values.walletStorageCredentials.json -}}
    {{- .Values.walletStorageCredentials.json -}}
{{- else if .Values.postgresql.enabled -}}
    '{"account":"{{ .Values.postgresql.auth.username }}","password":"$(POSTGRES_PASSWORD)","admin_account":"{{ .Values.walletStorageCredentials.admin_account }}","admin_password":"$(POSTGRES_POSTGRES_PASSWORD)"}'
{{- else -}}
    '{"account":"{{ .Values.walletStorageCredentials.account | default "acapy" }}","password":"$(POSTGRES_PASSWORD)","admin_account":"{{ .Values.walletStorageCredentials.admin_account }}","admin_password":"$(POSTGRES_POSTGRES_PASSWORD)"}'
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "acapy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "acapy.labels" -}}
helm.sh/chart: {{ include "acapy.chart" . }}
{{ include "acapy.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "acapy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "acapy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "acapy.imagePullSecrets" -}}
{{- include "common.images.pullSecrets" (dict "images" (list .Values.image) "global" .Values.global) -}}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "acapy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "common.names.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}
