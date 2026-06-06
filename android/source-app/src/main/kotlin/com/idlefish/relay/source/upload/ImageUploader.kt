package com.idlefish.relay.source.upload

import android.graphics.Bitmap
import com.idlefish.relay.shared.model.ApiResponse
import com.idlefish.relay.shared.network.ApiEndpoints
import com.idlefish.relay.shared.network.ServerConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.File

class ImageUploader {

    suspend fun uploadImage(bitmap: Bitmap, filename: String = "image.jpg"): ApiResponse {
        val url = ApiEndpoints.imagesUrl(ServerConfig.httpBaseUrl())

        val stream = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, 85, stream)
        val imageBytes = stream.toByteArray()

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", filename, imageBytes.toRequestBody("image/jpeg".toMediaType()))
            .build()

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
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

    suspend fun uploadImageFile(file: File): ApiResponse {
        val url = ApiEndpoints.imagesUrl(ServerConfig.httpBaseUrl())

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", file.name, file.asRequestBody("image/*".toMediaType()))
            .build()

        val request = Request.Builder()
            .url(url)
            .post(requestBody)
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
