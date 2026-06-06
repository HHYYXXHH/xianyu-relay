package com.idlefish.relay.source.ui

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.idlefish.relay.source.R
import com.idlefish.relay.source.data.AppDatabase
import com.idlefish.relay.source.service.NotificationMonitorService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class SetupActivity : AppCompatActivity() {

    private val handler = Handler(Looper.getMainLooper())
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var adapter: MsgAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_setup)

        val btnNotif: Button = findViewById(R.id.btn_open_settings)
        val statusText: TextView = findViewById(R.id.status_text)
        val statsText: TextView = findViewById(R.id.stats_text)
        val logText: TextView = findViewById(R.id.log_text)
        val msgList: RecyclerView = findViewById(R.id.msg_list)

        msgList.layoutManager = LinearLayoutManager(this)
        adapter = MsgAdapter()
        msgList.adapter = adapter

        btnNotif.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        refreshStatus(statusText)
        loadMessages(statsText)
        showLog(logText)

        var lastLogSize = NotificationMonitorService.log.size
        handler.postDelayed(object : Runnable {
            override fun run() {
                refreshStatus(statusText)
                val log = NotificationMonitorService.log
                if (log.size != lastLogSize) {
                    lastLogSize = log.size
                    showLog(logText)
                    loadMessages(statsText)
                }
                handler.postDelayed(this, 1500)
            }
        }, 1500)
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacksAndMessages(null)
    }

    private fun refreshStatus(tv: TextView) {
        val on = NotificationMonitorService.isNotificationListenerEnabled(this)
        tv.text = if (on) "运行中" else "未授权"
        tv.setTextColor(if (on) 0xFF4CAF50.toInt() else 0xFFFF5722.toInt())
    }

    private fun loadMessages(statsText: TextView) {
        scope.launch {
            try {
                val db = AppDatabase.getInstance(this@SetupActivity)
                val msgs = db.messageDao().getAll()
                val uploaded = msgs.count { it.uploaded }
                runOnUiThread {
                    statsText.text = "共 ${msgs.size} 条 | 已上传 $uploaded | 待上传 ${msgs.size - uploaded}"
                    adapter?.submitList(mapMessagesToDisplay(msgs))
                }
            } catch (_: Exception) {}
        }
    }

    private fun showLog(logText: TextView) {
        val log = NotificationMonitorService.log
        logText.text = if (log.isEmpty()) "等待通知…" else log.takeLast(6).joinToString("\n")
    }
}
