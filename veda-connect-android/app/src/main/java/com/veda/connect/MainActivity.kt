package com.veda.connect

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.veda.connect.core.AgentStateStore
import com.veda.connect.pairing.PairingStorage
import com.veda.connect.ui.VedaConnectApp
import com.veda.connect.ui.theme.VedaConnectTheme

class MainActivity : ComponentActivity() {
    private lateinit var storage: PairingStorage
    private var pendingServiceStart = false

    private val cameraPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { _ ->
        // The UI will react by showing the scanner if permission is granted.
    }

    private val notificationPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted || Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            if (pendingServiceStart) {
                pendingServiceStart = false
                startGatewayService()
            }
        } else {
            pendingServiceStart = false
            AgentStateStore.setError("Notification permission is required for Veda Connect.")
            AgentStateStore.setStatus("Notification permission denied")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        storage = PairingStorage(this)
        AgentStateStore.setCredential(storage.loadCredential())
        storage.loadGatewayHint()?.let {
            AgentStateStore.setPairingOffer(it)
            AgentStateStore.setGateway(
                com.veda.connect.core.GatewayEndpoint(
                    name = "Veda PC",
                    host = it.host,
                    port = it.port,
                )
            )
        }
        maybeStartService()
        ensureCameraPermission()
        setContent {
            VedaConnectTheme {
                VedaConnectApp(
                    onRequestCameraPermission = {
                        cameraPermission.launch(Manifest.permission.CAMERA)
                    },
                    onRequestNotificationPermission = {
                        notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                    },
                    onStartService = { maybeStartService() },
                )
            }
        }
    }

    private fun maybeStartService() {
        val endpoint = AgentStateStore.gateway.value
        if (endpoint != null || AgentStateStore.credential.value != null) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                pendingServiceStart = true
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                return
            }
            startGatewayService()
        }
    }

    private fun ensureCameraPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            cameraPermission.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startGatewayService() {
        val endpoint = AgentStateStore.gateway.value
        if (endpoint != null || AgentStateStore.credential.value != null) {
            val intent = Intent(this, VedaConnectForegroundService::class.java)
            ContextCompat.startForegroundService(this, intent)
        }
    }
}
