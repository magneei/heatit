# Heatit WiFi Cloud API Documentation

Reverse-engineered from the Heatit WiFi iOS app (com.thermofloor.heatitwifi, version 48).

## Architecture

The Heatit cloud is built on **Ouman Cloud** (tf.api.ouman-cloud.com) with AWS services:

- **Auth**: AWS Cognito (User Pool: `eu-west-1_2lWTXCKVV`, Client ID: `6spbss1b6lglcco8t3dtiv961e`)
- **API**: Multiple AWS AppSync GraphQL endpoints (discovered dynamically)
- **App framework**: React Native with aws-amplify/2.0.5

## Service Discovery

On startup, the app fetches endpoint URLs from `tf.api.ouman-cloud.com`:

| Service | URL | Purpose |
|---------|-----|---------|
| `GET /users/endpoint` | Returns GraphQL URL + Cognito IDs | User management |
| `GET /device/endpoint` | Returns GraphQL URL | Device tree, state, control |
| `GET /data/endpoint` | Returns GraphQL URL | Sensor data (temperatures, etc.) |
| `GET /events/endpoint` | Returns GraphQL URL | Events/alerts |
| `GET /ota/endpoint` | Returns GraphQL URL | Firmware updates |
| `GET /purchases/endpoint` | Returns 403 | Subscriptions (not active) |

## Authentication

AWS Cognito with email/password → JWT ID token (RS256, ~1h expiry).

- **User Pool ID**: `eu-west-1_2lWTXCKVV`
- **Client ID**: `6spbss1b6lglcco8t3dtiv961e`
- **Identity Pool ID**: `eu-west-1:a45f1401-b845-438a-a968-e8f308804a17`
- **Region**: `eu-west-1`

The JWT ID token is sent as `Authorization` header on all GraphQL requests.

## GraphQL Operations

### Users Service

**getCurrentUserDetails**
```graphql
query Query {
  getCurrentUserDetails {
    email
    organizationId
    admin
    superAdmin
    rdUser
    mssFreePass
    loggingAllowed
    appSettings
  }
}
```

### Device Service (main)

**getDeviceTree** — List all zones and devices
```graphql
query Query {
  getDeviceTree
}
```
Returns a JSON string (not object!) with nested tree structure:
```json
[{
  "i": {"id": "<org-id>", "attr": []},
  "c": [{
    "i": {"id": "<zone-id>", "attr": [], "state": {"displayName": "Bad", "timestamp": ..., "type": "zone"}},
    "c": [{
      "i": {
        "id": "<device-id>",
        "attr": [
          {"key": "devType", "value": "TF-MOD-WIFI-TFT"},
          {"key": "macAddr", "value": "34AB95932194"},
          {"key": "serialNum", "value": "2148030212"},
          {"key": "online", "value": "true"},
          {"key": "swVer", "value": "1.0.26"},
          {"key": "hwVer", "value": "C"},
          ...
        ],
        "type": "THERMOSTAT"
      },
      "t": 0
    }],
    "t": 2
  }],
  "t": 1
}]
```
Tree node types: `t=0` = device, `t=1` = organization, `t=2` = zone.

**getDeviceState** — Get device configuration and state
```graphql
query Query($deviceId: ID!) {
  getDeviceState(deviceId: $deviceId) {
    desired
    reported
    metadata
    timestamp
    version
  }
}
```
Returns AWS IoT shadow format. The `reported` field (JSON string):
```json
{
  "deviceId": "0be19199-...",
  "setPoint": 230,           // Target temp × 10 (23.0°C)
  "currentSetPoint": 230,    // Active setpoint × 10
  "awaySetPoint": 110,       // Away/ECO temp × 10 (11.0°C)
  "opMode": 0,               // 0=HOME, 1=AWAY, 2=TIMEPLAN, 3=ANTIFREEZE, 4=ENERGY_MGMT
  "setRegP": 3,              // Regulation parameter
  "tempUnit": 0,             // 0=Celsius, 1=Fahrenheit
  "displayName": "BadGulv",
  "advCfg": "AwEAAAUAADIAkAHcBTIAkAEyAJAB",  // Base64-encoded advanced config
  "display": "AQADCgAACgAF",                   // Display settings
  "wizard": "AgAAAQCQAdIA",                     // Setup wizard state
  "wClk": "AAD//wAA//...",                      // Weekly clock/schedule
  "custom": 1,
  "tz": "UTC+1",
  "otaId": "",
  "cmd": "ping(1774815907907)",
  "devType": "TF-MOD-WIFI-TFT",
  "errorCodes": 0,
  "statusCodes": 0,
  "online": true,
  "macAddr": "34AB95932194",
  "serialNum": "2148030212",
  "swVer": "1.0.26",
  "hwVer": "C",
  "hwProperties": 5,
  "msgId": 82,
  "expired": false
}
```

**requestStateChange** — Set device parameters (mutation)
```graphql
mutation Mutation($deviceId: ID!, $state: AWSJSON!, $getFullState: Boolean) {
  requestStateChange(deviceId: $deviceId, state: $state, getFullState: $getFullState)
}
```
The `state` variable is a JSON string. Known commands:
- `{"opMode": 0}` — Home (normal heating)
- `{"opMode": 1}` — Away (reduced temp, uses awaySetPoint)
- `{"opMode": 2}` — Timeplan (weekly schedule)
- `{"opMode": 3}` — Antifreeze (frost protection)
- `{"opMode": 4}` — Energy Management
- `{"setPoint": 230}` — Set temperature to 23.0°C (value × 10)
- `{"cmd": "ping(timestamp)"}` — Keepalive ping

### Data Service

**getLatestData** — Get current sensor readings
```graphql
query Query($deviceId: String!) {
  getLatestData(deviceId: $deviceId) {
    deviceId
    timestamp
    sessionId
    type
    data
  }
}
```
The `data` field (JSON string):
```json
{
  "subDevices": [],
  "currentTemp": 231,          // Current temperature × 10 (23.1°C)
  "currentSetPoint": 230,      // Active setpoint × 10
  "floorSensTemp": 231,        // Floor sensor × 10
  "roomSensTemp": 179,         // Room sensor × 10 (17.9°C)
  "espSensorTemp": 275,        // ESP/external sensor × 10
  "compSensTemp": 365,         // Compensation sensor × 10
  "deviceState": 0,            // 0=idle, 1=heating(?), 2=cooling(?)
  "relayState": 0,             // 0=off, 1=on
  "relayOnTime": 34010243,     // Total relay on time (seconds?)
  "rssi": -50,                 // WiFi signal strength
  "roomSensAdc": 530,          // Raw ADC values
  "floorSensAdc": 338,
  "compSensAdc": 576,
  "espSensorAdc": 483,
  "roomSensTempRaw": 233,
  "TempCtrlPIDI": 0,
  "CompMultiplier": 201
}
```

### Events Service

**getEventsForDevices** — Get alerts/events
```graphql
query Query($deviceIds: [String]!, $includeInactive: Boolean) {
  getEventsForDevices(deviceIds: $deviceIds, includeInactive: $includeInactive) {
    items {
      deviceId
      timestamp
      eventId
      updatedTimestamp
      type
      eventState
      severity
      sensorName
      sensorValue
      metadata
      seen
      subDeviceId
    }
  }
}
```

### OTA Service

**getCurrentOtaState** / **getOtaUpdate** — Firmware update status (not needed for integration)

## Temperature Values

All temperature values are integers representing **°C × 10**:
- `230` = 23.0°C
- `179` = 17.9°C
- `110` = 11.0°C
