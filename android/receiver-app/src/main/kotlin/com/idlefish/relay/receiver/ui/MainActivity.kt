package com.idlefish.relay.receiver.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.service.WebSocketService
import com.idlefish.relay.shared.network.ServerConfig
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        requestNotificationPermission()
        startWebSocketService()

        val eventId = intent.getStringExtra("event_id")
        if (eventId != null) {
            showDetail(eventId)
        } else if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.fragment_container, EventListFragment())
                .commit()
        }

        val statusText: TextView = findViewById(R.id.connection_status)
        val wsUrl = "ws://${ServerConfig.host}:${ServerConfig.wsPort}"
        statusText.text = "连接中… $wsUrl"

        lifecycleScope.launch {
            WebSocketService.connectionState.collect { connected ->
                statusText.text = if (connected) "已连接 $wsUrl" else "断开 $wsUrl"
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    REQ_POST_NOTIFICATIONS,
                )
            }
        }
    }

    private fun startWebSocketService() {
        val intent = Intent(this, WebSocketService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    fun showDetail(eventId: String) {
        val detailFragment = EventDetailFragment.newInstance(eventId)
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, detailFragment)
            .addToBackStack(null)
            .commit()
    }

    override fun onBackPressed() {
        if (supportFragmentManager.backStackEntryCount > 0) {
            super.onBackPressed()
        }
    }

    companion object {
        private const val REQ_POST_NOTIFICATIONS = 100
    }
}
