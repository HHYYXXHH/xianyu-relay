package com.idlefish.relay.source.ui

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.idlefish.relay.shared.network.ServerConfig
import com.idlefish.relay.source.IdlefishRelayApp
import com.idlefish.relay.source.R

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val hostInput: EditText = findViewById(R.id.input_host)
        val httpPortInput: EditText = findViewById(R.id.input_http_port)
        val wsPortInput: EditText = findViewById(R.id.input_ws_port)
        val saveBtn: Button = findViewById(R.id.btn_save)

        hostInput.setText(ServerConfig.host)
        httpPortInput.setText(ServerConfig.httpPort.toString())
        wsPortInput.setText(ServerConfig.wsPort.toString())

        saveBtn.setOnClickListener {
            val host = hostInput.text.toString().trim()
            val httpPort = httpPortInput.text.toString().trim().toIntOrNull()
            val wsPort = wsPortInput.text.toString().trim().toIntOrNull()

            if (host.isEmpty() || httpPort == null || wsPort == null) {
                Toast.makeText(this, "请填写完整信息", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            ServerConfig.host = host
            ServerConfig.httpPort = httpPort
            ServerConfig.wsPort = wsPort
            ServerConfig.saveToPreferences(IdlefishRelayApp.instance.prefs)

            Toast.makeText(this, "保存成功", Toast.LENGTH_SHORT).show()
            finish()
        }
    }
}
