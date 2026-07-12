package com.veda.connect.network

import android.content.Context
import android.os.SystemClock
import com.veda.connect.commands.DeviceCommandHandler
import com.veda.connect.core.AgentStateStore
import com.veda.connect.core.VedaProtocol
import com.veda.connect.core.ChatMessage
import com.veda.connect.core.ConnectionState
import com.veda.connect.core.DeviceCredential
import com.veda.connect.core.DeviceSnapshot
import com.veda.connect.core.GatewayEndpoint
import com.veda.connect.core.PairingOffer
import com.veda.connect.pairing.PairingStorage
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import kotlin.math.min

class VedaWebSocketClient(
    private val context: Context,
    private val storage: PairingStorage,
    private val commandHandler: DeviceCommandHandler,
) {
    private val client = OkHttpClient.Builder()
        .retryOnConnectionFailure(true)
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private var socket: WebSocket? = null
    private var currentEndpoint: GatewayEndpoint? = null
    private var currentOffer: PairingOffer? = null
    private var currentCredential: DeviceCredential? = null
    private var manualDisconnect = false
    private var reconnectAttempt = 0
    private var lastConnectUptime = 0L

    fun connect(endpoint: GatewayEndpoint, credential: DeviceCredential? = storage.loadCredential(), offer: PairingOffer? = null) {
        if (socket != null && currentEndpoint == endpoint) {
            currentCredential = credential ?: currentCredential
            currentOffer = offer ?: currentOffer
            AgentStateStore.setGateway(endpoint)
            return
        }
        currentEndpoint = endpoint
        currentCredential = credential
        currentOffer = offer
        manualDisconnect = false
        reconnectAttempt = 0
        lastConnectUptime = SystemClock.elapsedRealtime()
        AgentStateStore.setGateway(endpoint)
        AgentStateStore.setConnectionState(ConnectionState.CONNECTING)
        AgentStateStore.setStatus("Connecting to ${endpoint.name}")

        socket?.close(1000, "Reconnecting")
        socket = client.newWebSocket(
            Request.Builder().url("ws://${endpoint.host}:${endpoint.port}/ws").build(),
            VedaSocketListener(),
        )
    }

    fun disconnect() {
        manualDisconnect = true
        socket?.close(1000, "Disconnected by user")
        socket = null
        AgentStateStore.setConnectionState(ConnectionState.DISCONNECTED)
        AgentStateStore.setStatus("Disconnected")
    }

    private fun reconnectLater() {
        if (manualDisconnect) return
        val endpoint = currentEndpoint ?: return
        reconnectAttempt += 1
        AgentStateStore.setConnectionState(ConnectionState.RECONNECTING)
        val delayMs = min(30_000L, 1_000L * (1 shl min(reconnectAttempt, 5)))
        AgentStateStore.setStatus("Reconnecting in ${delayMs / 1000}s")
        Thread {
            try {
                Thread.sleep(delayMs)
            } catch (_: InterruptedException) {
                return@Thread
            }
            if (!manualDisconnect && currentEndpoint == endpoint) {
                connect(endpoint, currentCredential, currentOffer)
            }
        }.start()
    }

    private fun send(json: JSONObject) {
        socket?.send(json.toString())
    }

    private fun batterySnapshot(): Pair<Int, Boolean> {
        val battery = commandHandler.handle("get_battery", emptyMap()).data
        val percentage = (battery["percentage"] as? Int) ?: -1
        val charging = (battery["charging"] as? Boolean) ?: false
        return percentage to charging
    }

    private fun buildSnapshot(): DeviceSnapshot {
        val credential = currentCredential
        val (percentage, charging) = batterySnapshot()
        return DeviceSnapshot(
            deviceId = credential?.deviceId,
            deviceName = credential?.deviceName ?: android.os.Build.MODEL ?: "Android",
            androidVersion = android.os.Build.VERSION.RELEASE ?: "Unknown",
            agentVersion = "1.0.0",
            batteryPercentage = percentage,
            charging = charging,
            wifiEnabled = true,
            capabilities = listOf(
                "device_info",
                "battery",
                "flashlight",
                "volume",
                "media",
                "launch_app",
                "apps",
                "open_url",
                "wifi_state",
            ),
        )
    }

    private fun sendHello() {
        send(VedaProtocol.hello(buildSnapshot()))
        AgentStateStore.setStatus("Awaiting approval")
    }

    private fun sendPairRequest() {
        val offer = currentOffer ?: run {
            sendHello()
            return
        }
        val snapshot = buildSnapshot().toJson()
            .put("pairing_token", offer.pairingToken)
            .put("pairing_code", offer.pairingCode)
        send(VedaProtocol.envelope(VedaProtocol.PAIR_REQUEST, snapshot))
        AgentStateStore.setStatus("Pairing request sent")
    }

    private fun sendAuthenticate() {
        val credential = currentCredential ?: storage.loadCredential()
        if (credential == null) {
            sendHello()
            return
        }
        currentCredential = credential
        send(VedaProtocol.authenticate(credential))
        AgentStateStore.setStatus("Authenticating")
    }

    private fun handleCommandMessage(root: JSONObject) {
        val requestId = root.optString("request_id")
        val payload = root.optJSONObject("payload") ?: JSONObject()
        val action = payload.optString("action")
        val params = payload.optJSONObject("parameters") ?: JSONObject()
        val parameterMap = buildMap<String, Any?> {
            params.keys().forEach { key ->
                put(key, params.opt(key))
            }
        }
        val result = commandHandler.handle(action, parameterMap)
        val response = VedaProtocol.envelope(
            VedaProtocol.RESULT,
            result.toJson(),
            requestId = requestId,
        )
        send(response)
    }

    private fun handlePairApproved(root: JSONObject) {
        val payload = root.optJSONObject("payload") ?: JSONObject()
        val device = payload.optJSONObject("device") ?: JSONObject()
        val secret = payload.optString("device_secret")
        val deviceId = device.optString("device_id")
        val deviceName = device.optString("name", android.os.Build.MODEL ?: "Android")
        val credential = DeviceCredential(
            deviceId = deviceId,
            deviceSecret = secret,
            deviceName = deviceName,
            gatewayHost = currentEndpoint?.host.orEmpty(),
            gatewayPort = currentEndpoint?.port ?: 8765,
        )
        storage.saveCredential(credential)
        currentCredential = credential
        AgentStateStore.setCredential(credential)
        AgentStateStore.setStatus("Pair approved")
        sendAuthenticate()
    }

    private inner class VedaSocketListener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
            socket = webSocket
            reconnectAttempt = 0
            AgentStateStore.setConnectionState(ConnectionState.CONNECTING)
            if (currentCredential != null || storage.loadCredential() != null) {
                sendAuthenticate()
            } else if (currentOffer != null) {
                sendPairRequest()
            } else {
                sendHello()
            }
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            runCatching {
                val root = JSONObject(text)
                val type = root.optString("type")
                when (type) {
                    VedaProtocol.PAIR_REQUEST -> {
                        AgentStateStore.setStatus("Waiting for approval")
                    }
                    VedaProtocol.PAIR_APPROVED -> handlePairApproved(root)
                    VedaProtocol.DEVICE_ONLINE -> {
                        AgentStateStore.setConnectionState(ConnectionState.CONNECTED)
                        AgentStateStore.setStatus("Connected")
                    }
                    VedaProtocol.CAPABILITIES -> {
                        AgentStateStore.addLog("Capabilities synced")
                    }
                    VedaProtocol.EXECUTE -> handleCommandMessage(root)
                    VedaProtocol.PING -> {
                        send(VedaProtocol.envelope(VedaProtocol.PONG, JSONObject().put("status", "ok"), requestId = root.optString("request_id")))
                    }
                    VedaProtocol.ERROR -> {
                        AgentStateStore.setError(root.optJSONObject("payload")?.optString("error"))
                    }
                    VedaProtocol.CHAT_MESSAGE -> {
                        val payload = root.optJSONObject("payload") ?: return
                        val role = payload.optString("role", "system")
                        val text = payload.optString("text", "")
                        val msgId = root.optString("request_id")
                        val timestamp = System.currentTimeMillis()
                        val msg = ChatMessage(msgId, role, text, timestamp, "Sent")
                        AgentStateStore.addChatMessage(msg)
                    }
                }
            }.onFailure {
                AgentStateStore.setError(it.message)
            }
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            onMessage(webSocket, bytes.utf8())
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            socket = null
            AgentStateStore.addLog("Socket closed: $code $reason")
            AgentStateStore.setConnectionState(ConnectionState.DISCONNECTED)
            AgentStateStore.setStatus("Disconnected")
            reconnectLater()
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
            socket = null
            AgentStateStore.addLog("Socket failure: ${t.message}")
            AgentStateStore.setConnectionState(ConnectionState.DISCONNECTED)
            AgentStateStore.setStatus("Connection failed")
            reconnectLater()
        }
    }

    fun sendChatMessage(text: String) {
        val payload = VedaProtocol.chatMessage(text)
        val msgId = payload.getString("request_id")
        val timestamp = System.currentTimeMillis()
        val pending = ChatMessage(msgId, "user", text, timestamp, "Sending...")
        AgentStateStore.addChatMessage(pending)
        send(payload)
        val sent = pending.copy(status = "Sent")
        AgentStateStore.addChatMessage(sent)
    }
}
