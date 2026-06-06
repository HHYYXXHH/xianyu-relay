package com.idlefish.relay.source.ui

import android.app.AlertDialog
import android.graphics.Color
import android.text.TextUtils
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.idlefish.relay.source.R
import com.idlefish.relay.source.data.entity.MessageEntity
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class MsgDisplay(
    val title: String,
    val summary: String,
    val fullText: String,
    val uploaded: Boolean,
    val createdAt: Long,
)

class MsgAdapter : RecyclerView.Adapter<MsgAdapter.ViewHolder>() {

    private var items: List<MsgDisplay> = emptyList()

    fun submitList(list: List<MsgDisplay>) {
        items = list
        notifyDataSetChanged()
    }

    override fun getItemCount() = items.size

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_message, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]

        holder.titleText.text = item.title
        // 摘要：单行省略
        holder.summaryText.text = item.summary
        holder.summaryText.maxLines = 1
        holder.summaryText.ellipsize = TextUtils.TruncateAt.END

        if (item.uploaded) {
            holder.statusText.text = "已上传"
            holder.statusText.setTextColor(0xFF4CAF50.toInt())
        } else {
            holder.statusText.text = "待上传"
            holder.statusText.setTextColor(0xFFFF9800.toInt())
        }

        val sdf = SimpleDateFormat("HH:mm", Locale.getDefault())
        holder.timeText.text = sdf.format(Date(item.createdAt))

        // 点击查看完整内容
        holder.itemView.setOnClickListener {
            AlertDialog.Builder(holder.itemView.context)
                .setTitle(item.title)
                .setMessage(item.fullText)
                .setPositiveButton("关闭", null)
                .show()
        }
    }

    class ViewHolder(view: android.view.View) : RecyclerView.ViewHolder(view) {
        val titleText: TextView = view.findViewById(R.id.item_title)
        val summaryText: TextView = view.findViewById(R.id.item_summary)
        val statusText: TextView = view.findViewById(R.id.item_status)
        val timeText: TextView = view.findViewById(R.id.item_time)
    }
}

fun mapMessagesToDisplay(messages: List<MessageEntity>): List<MsgDisplay> {
    return messages.mapNotNull { msg ->
        try {
            val json = JSONObject(msg.eventJson)
            val text = json.optString("content_text",
                json.optString("summary", json.optString("image_ocr_text", ""))).ifBlank { "(无内容)" }
            MsgDisplay(
                title = json.optString("title", json.optString("thread_key", "未知")),
                summary = text.take(40),
                fullText = text,
                uploaded = msg.uploaded,
                createdAt = msg.createdAt,
            )
        } catch (e: Exception) {
            null
        }
    }
}
