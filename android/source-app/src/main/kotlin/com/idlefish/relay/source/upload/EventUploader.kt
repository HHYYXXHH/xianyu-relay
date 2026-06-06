package com.idlefish.relay.source.upload

import com.idlefish.relay.shared.model.ApiResponse
import com.idlefish.relay.shared.network.ApiEndpoints
import com.idlefish.relay.shared.network.ServerConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class EventUploader {

    suspend fun uploadEvent(event: JSONObject): ApiResponse {
        val url = ApiEndpoints.eventsUrl(ServerConfig.httpBaseUrl())
        val body = event.toString()
        val request = Request.Builder()
            .url(url)
            .post(body.toRequestBody("application/json".toMediaType()))
            .build()

        return try {
            val response = HttpClient.instance.newCall(request).execute()
            val responseBody = response.body?.string() ?: ""
            ApiResponse(
                ok = response.isSuccessful,
                status = response.code,
                body = responseBody,
            )
        } catch (e: Exception) {
            ApiResponse(ok = false, status = 500, body = """{"error":"${e.message}"}""")
        }
    }
}
