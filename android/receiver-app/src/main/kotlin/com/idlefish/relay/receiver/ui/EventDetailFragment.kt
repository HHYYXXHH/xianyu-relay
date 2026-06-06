package com.idlefish.relay.receiver.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.bumptech.glide.Glide
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.data.EventUiModel
import com.idlefish.relay.receiver.service.WebSocketService
import com.idlefish.relay.shared.network.ApiEndpoints
import com.idlefish.relay.shared.network.ServerConfig
import com.idlefish.relay.shared.util.TimestampUtil
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class EventDetailFragment : Fragment() {

    private var currentEventId: String? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View? {
        return inflater.inflate(R.layout.fragment_event_detail, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val eventId = arguments?.getString("event_id") ?: currentEventId ?: return
        currentEventId = eventId

        val repository = WebSocketService.getRepository()
        val event = repository.getEvent(eventId) ?: return

        render(view, event)
    }

    private fun render(view: View, event: EventUiModel) {
        val detailText: TextView = view.findViewById(R.id.detail_text)
        val imagePreview: ImageView = view.findViewById(R.id.image_preview)
        val handleBtn: Button = view.findViewById(R.id.btn_handle)
        val attentionLabel: TextView = view.findViewById(R.id.attention_label)

        val sb = StringBuilder()
        sb.appendLine("事件ID: ${event.eventId}")
        sb.appendLine("类型: ${event.eventType}/${event.contentType}")
        sb.appendLine("摘要: ${event.summary}")
        sb.appendLine("时间: ${event.timestamp}")
        sb.appendLine("OCR状态: ${event.ocrStatus}")
        sb.appendLine("上传状态: ${event.uploadStatus}")

        if (event.ocrError.isNotBlank()) {
            sb.appendLine("---")
            sb.appendLine("OCR错误: ${event.ocrError}")
        }
        if (event.errorCode.isNotBlank()) {
            sb.appendLine("错误码: ${event.errorCode}")
            sb.appendLine("错误信息: ${event.errorMessage}")
        }
        if (event.imageOcrText.isNotBlank()) {
            sb.appendLine("---")
            sb.appendLine("OCR文本:")
            sb.appendLine(event.imageOcrText.take(500))
        }

        detailText.text = sb.toString()

        // 加载图片
        if (event.imageRefs.isNotEmpty()) {
            val imageUrl = ApiEndpoints.imageDownloadUrl(ServerConfig.httpBaseUrl(), event.imageRefs.first())
            Glide.with(requireContext())
                .load(imageUrl)
                .placeholder(android.R.drawable.ic_menu_gallery)
                .error(android.R.drawable.ic_menu_report_image)
                .into(imagePreview)
            imagePreview.visibility = View.VISIBLE
        } else {
            imagePreview.visibility = View.GONE
        }

        // 需要关注标签
        if (event.needAttention && !event.isHandled) {
            attentionLabel.visibility = View.VISIBLE
            attentionLabel.text = "需要人工处理！"
            attentionLabel.setTextColor(0xFFCC0000.toInt())
            handleBtn.isEnabled = true
        } else if (event.isHandled) {
            attentionLabel.visibility = View.VISIBLE
            attentionLabel.text = "已处理"
            attentionLabel.setTextColor(0xFF339900.toInt())
            handleBtn.isEnabled = false
            handleBtn.text = "已处理"
        } else {
            attentionLabel.visibility = View.GONE
            handleBtn.isEnabled = false
        }

        // 标记已处理
        handleBtn.setOnClickListener {
            handleBtn.isEnabled = false
            handleBtn.text = "处理中…"
            markAsHandled(event.eventId) { success ->
                activity?.runOnUiThread {
                    if (success) {
                        WebSocketService.getRepository().markHandled(event.eventId)
                        attentionLabel.visibility = View.VISIBLE
                        attentionLabel.text = "已处理"
                        attentionLabel.setTextColor(0xFF339900.toInt())
                        handleBtn.text = "已处理"
                        Toast.makeText(requireContext(), "已标记为已处理", Toast.LENGTH_SHORT).show()
                    } else {
                        handleBtn.isEnabled = true
                        handleBtn.text = "标记已处理"
                        Toast.makeText(requireContext(), "请求失败，请重试", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }

    private fun markAsHandled(eventId: String, callback: (Boolean) -> Unit) {
        Thread {
            try {
                val url = ApiEndpoints.attentionStatusUrl(ServerConfig.httpBaseUrl())
                val body = JSONObject().apply {
                    put("event_id", eventId)
                    put("attention_status", "handled")
                    put("handled_at", TimestampUtil.now())
                }
                val requestBody = body.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url(url).post(requestBody).build()
                val response = OkHttpClient().newCall(request).execute()
                callback(response.isSuccessful)
            } catch (e: Exception) {
                callback(false)
            }
        }.start()
    }

    companion object {
        fun newInstance(eventId: String): EventDetailFragment {
            val fragment = EventDetailFragment()
            fragment.arguments = Bundle().apply {
                putString("event_id", eventId)
            }
            return fragment
        }
    }
}
