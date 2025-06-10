/**
 * Copyright (C) 2015 Garmin International Ltd.
 * Subject to Garmin SDK License Agreement and Wearables Application Developer Agreement.
 */
package com.garmin.android.apps.connectiq.sample.comm.activities

import android.annotation.SuppressLint
import android.app.Activity
import android.os.Bundle
import android.util.Log
import android.view.Menu
import android.view.MenuItem
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.garmin.android.apps.connectiq.sample.comm.R
import com.garmin.android.apps.connectiq.sample.comm.adapter.IQDeviceAdapter
import com.garmin.android.connectiq.ConnectIQ
import com.garmin.android.connectiq.IQApp
import com.garmin.android.connectiq.IQDevice
import com.garmin.android.connectiq.exception.InvalidStateException
import com.garmin.android.connectiq.exception.ServiceUnavailableException

class MainActivity : Activity() {

    private lateinit var connectIQ: ConnectIQ
    private lateinit var adapter: IQDeviceAdapter

    // Nouveaux éléments pour la fréquence cardiaque
    private lateinit var heartRateTextView: TextView
    private lateinit var requestButton: Button
    private lateinit var statusTextView: TextView

    // Variables pour la communication avec l'app Garmin
    private var selectedDevice: IQDevice? = null
    private var targetApp: IQApp? = null

    // Remplacez par l'ID de votre app Garmin Connect IQ
    private val GARMIN_APP_ID = "9f48c3d6e1a74b0fa5d31f09c6d3a13e"



    private var isSdkReady = false

    private val connectIQListener: ConnectIQ.ConnectIQListener =
        object : ConnectIQ.ConnectIQListener {
            override fun onInitializeError(errStatus: ConnectIQ.IQSdkErrorStatus) {
                setEmptyState(getString(R.string.initialization_error) + ": " + errStatus.name)
                updateStatus("Erreur d'initialisation: ${errStatus.name}")
                isSdkReady = false
            }

            override fun onSdkReady() {
                loadDevices()
                updateStatus("SDK prêt")
                isSdkReady = true
            }

            override fun onSdkShutDown() {
                updateStatus("SDK arrêté")
                isSdkReady = false
            }
        }

    @SuppressLint("MissingInflatedId")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        setupUi()
        setupConnectIQSdk()
        setupHeartRateFeatures()
    }

    public override fun onResume() {
        super.onResume()
        if (isSdkReady) {
            loadDevices()
        }
    }

    public override fun onDestroy() {
        super.onDestroy()
        releaseConnectIQSdk()
    }

    private fun releaseConnectIQSdk() {
        try {
            // It is a good idea to unregister everything and shut things down to
            // release resources and prevent unwanted callbacks.
            connectIQ.unregisterAllForEvents()
            connectIQ.shutdown(this)
        } catch (e: InvalidStateException) {
            // This is usually because the SDK was already shut down
            // so no worries.
        }
    }

    private fun setupUi() {
        // Setup UI existant
        adapter = IQDeviceAdapter { onItemClick(it) }
        val recyclerView = findViewById<RecyclerView>(R.id.recyclerView)
        if (recyclerView != null) {
            recyclerView.layoutManager = LinearLayoutManager(this)
            recyclerView.adapter = adapter
        } else {
            Log.e("MainActivity", "La RecyclerView est null dans setupUi() !")
        }
    }

    private fun setupHeartRateFeatures() {
        // Initialiser les nouveaux éléments UI pour la fréquence cardiaque
        heartRateTextView = findViewById(R.id.heartRateValue)
        requestButton = findViewById(R.id.requestHeartRateButton)
        statusTextView = findViewById(R.id.statusText)

        // Configuration du bouton de demande
        requestButton.setOnClickListener {
            requestHeartRateFromWatch()
        }

        // Initialiser les textes
        heartRateTextView.text = "-- bpm"
        statusTextView.text = "En attente de connexion..."
        requestButton.isEnabled = false
    }

    private fun onItemClick(device: IQDevice) {
        // Sélectionner le device et chercher l'app
        selectedDevice = device
        updateStatus("Appareil sélectionné: ${device.friendlyName}")
        findWatchApp(device)

        // Optionnel: toujours ouvrir DeviceActivity
        startActivity(DeviceActivity.getIntent(this, device))
    }

    private fun findWatchApp(device: IQDevice) {
        try {
            connectIQ.getApplicationInfo(GARMIN_APP_ID, device,
                object : ConnectIQ.IQApplicationInfoListener {
                    override fun onApplicationInfoReceived(app: IQApp) {
                        targetApp = app
                        selectedDevice = device
                        Log.d("MainActivity", "App trouvée: ${app.displayName}")
                        updateStatus("App connectée: ${app.displayName}")
                        registerForAppMessages()
                        requestButton.isEnabled = true
                    }

                    override fun onApplicationNotInstalled(applicationId: String) {
                        Log.e("MainActivity", "App non installée: $applicationId")
                        updateStatus("Votre app n'est pas installée sur la montre")
                        requestButton.isEnabled = false
                    }
                })
        } catch (e: Exception) {
            Log.e("MainActivity", "Erreur lors de la recherche de l'app", e)
            updateStatus("Erreur de connexion à l'app")
        }
    }

    private fun registerForAppMessages() {
        selectedDevice?.let { device ->
            targetApp?.let { app ->
                try {
                    connectIQ.registerForAppEvents(device, app,
                        object : ConnectIQ.IQApplicationEventListener {
                            override fun onMessageReceived(
                                device: IQDevice,
                                app: IQApp,
                                message: List<Any>,
                                status: ConnectIQ.IQMessageStatus
                            ) {
                                if (status == ConnectIQ.IQMessageStatus.SUCCESS) {
                                    handleHeartRateMessage(message)
                                } else {
                                    Log.w("MainActivity", "Message reçu avec erreur: $status")
                                }
                            }
                        })
                } catch (e: Exception) {
                    Log.e("MainActivity", "Erreur lors de l'enregistrement des messages", e)
                }
            }
        }
    }

    private fun handleHeartRateMessage(message: List<Any>) {
        try {
            Log.d("MainActivity", "Message reçu: $message")

            // Le message peut arriver sous différentes formes
            if (message.isNotEmpty()) {
                val data = message[0]

                when (data) {
                    is Map<*, *> -> {
                        val type = data["type"] as? String
                        if (type == "heartRate") {
                            val heartRate = (data["heartRate"] as? Number)?.toInt() ?: 0
                            val timestamp = (data["timestamp"] as? Number)?.toLong() ?: 0

                            runOnUiThread {
                                updateHeartRate(heartRate)
                                Log.d("MainActivity", "Fréquence cardiaque reçue: $heartRate bpm")
                            }
                        }
                    }
                    is Number -> {
                        // Si c'est juste un nombre (fréquence cardiaque directe)
                        val heartRate = data.toInt()
                        runOnUiThread {
                            updateHeartRate(heartRate)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "Erreur lors du traitement du message", e)
            runOnUiThread {
                updateStatus("Erreur de traitement des données")
            }
        }
    }

    private fun requestHeartRateFromWatch() {
        selectedDevice?.let { device ->
            targetApp?.let { app ->
                try {
                    updateStatus("Demande de fréquence cardiaque...")

                    val message = mapOf("request" to "heartRate")

                    connectIQ.sendMessage(device, app, message,
                        object : ConnectIQ.IQSendMessageListener {
                            override fun onMessageStatus(
                                device: IQDevice,
                                app: IQApp,
                                status: ConnectIQ.IQMessageStatus
                            ) {
                                runOnUiThread {
                                    when (status) {
                                        ConnectIQ.IQMessageStatus.SUCCESS -> {
                                            Log.d("MainActivity", "Demande envoyée avec succès")
                                            updateStatus("Demande envoyée, en attente...")
                                        }
                                        ConnectIQ.IQMessageStatus.FAILURE_UNKNOWN -> {
                                            Log.e("MainActivity", "Échec de l'envoi")
                                            updateStatus("Erreur de communication")
                                        }
                                        ConnectIQ.IQMessageStatus.FAILURE_INVALID_DEVICE -> {
                                            updateStatus("Appareil non valide")
                                        }
                                        ConnectIQ.IQMessageStatus.FAILURE_DEVICE_NOT_CONNECTED -> {
                                            updateStatus("Appareil non connecté")
                                        }
                                        else -> {
                                            Log.w("MainActivity", "Statut: $status")
                                            updateStatus("Statut: $status")
                                        }
                                    }
                                }
                            }
                        })
                } catch (e: Exception) {
                    Log.e("MainActivity", "Erreur lors de l'envoi du message", e)
                    updateStatus("Erreur lors de l'envoi")
                }
            } ?: run {
                updateStatus("App non connectée")
            }
        } ?: run {
            updateStatus("Aucun appareil sélectionné")
        }
    }

    private fun updateHeartRate(heartRate: Int) {
        heartRateTextView.text = "$heartRate bpm"
        updateStatus("Dernière mise à jour: ${System.currentTimeMillis() / 1000}")
    }

    private fun updateStatus(message: String) {
        statusTextView.text = message
    }

    private fun setupConnectIQSdk() {
        // Here we are specifying that we want to use a WIRELESS bluetooth connection.
        // We could have just called getInstance() which would by default create a version
        // for WIRELESS, unless we had previously gotten an instance passing TETHERED
        // as the connection type.
        connectIQ = ConnectIQ.getInstance(this, ConnectIQ.IQConnectType.WIRELESS)

        // Initialize the SDK
        connectIQ.initialize(this, true, connectIQListener)
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.main, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.load_devices -> {
                loadDevices()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    fun loadDevices() {
        try {
            // Retrieve the list of known devices.
            val devices = connectIQ.knownDevices ?: listOf()
            // OR You can use getConnectedDevices to retrieve the list of connected devices only.
            // val devices = connectIQ.connectedDevices ?: listOf()

            // Get the connectivity status for each device for initial state.
            devices.forEach {
                it.status = connectIQ.getDeviceStatus(it)
            }

            // Update ui list with the devices data
            adapter.submitList(devices)

            // Let's register for device status updates.
            devices.forEach {
                connectIQ.registerForDeviceEvents(it) { device, status ->
                    adapter.updateDeviceStatus(device, status)
                }
            }

            updateStatus("${devices.size} appareil(s) trouvé(s)")

        } catch (exception: InvalidStateException) {
            // This generally means you forgot to call initialize(), but since
            // we are in the callback for initialize(), this should never happen
            Log.e("MainActivity", "InvalidStateException", exception)
            updateStatus("Erreur d'état du SDK")
        } catch (exception: ServiceUnavailableException) {
            // This will happen if for some reason your app was not able to connect
            // to the ConnectIQ service running within Garmin Connect Mobile.  This
            // could be because Garmin Connect Mobile is not installed or needs to
            // be upgraded.
            setEmptyState(getString(R.string.service_unavailable))
            updateStatus("Service Garmin Connect indisponible")
        }
    }

    private fun setEmptyState(text: String) {
        findViewById<TextView>(android.R.id.empty)?.text = text
    }

}