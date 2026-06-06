package com.idlefish.relay.receiver.ui.adapter

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.data.EventUiModel

class EventAdapter(
    private val onItemClick: (EventUiModel) -> Unit,
) : ListAdapter<EventUiModel, EventAdapter.ViewHolder>(DiffCallback) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_event, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(getItem(position), onItemClick)
    }

    class ViewHolder(root: View) : RecyclerView.ViewHolder(root) {
        private val attentionIcon: TextView = root.findViewById(R.id.attention_icon)
        private val summaryText: TextView = root.findViewById(R.id.summary_text)
        private val eventIdText: TextView = root.findViewById(R.id.event_id_text)
        private val timestampText: TextView = root.findViewById(R.id.timestamp_text)

        fun bind(item: EventUiModel, onClick: (EventUiModel) -> Unit) {
            if (item.needAttention && !item.isHandled) {
                attentionIcon.visibility = View.VISIBLE
                attentionIcon.text = "[!]"
                itemView.setBackgroundColor(0xFFFFF0F0.toInt())
                summaryText.setTextColor(0xFFCC0000.toInt())
            } else {
                attentionIcon.visibility = View.INVISIBLE
                itemView.setBackgroundColor(Color.WHITE)
                summaryText.setTextColor(0xFF333333.toInt())
            }

            summaryText.text = item.summary.ifBlank { "(无内容)" }
            eventIdText.text = item.eventId
            timestampText.text = item.timestamp
            itemView.setOnClickListener { onClick(item) }
        }
    }

    object DiffCallback : DiffUtil.ItemCallback<EventUiModel>() {
        override fun areItemsTheSame(old: EventUiModel, new: EventUiModel) =
            old.eventId == new.eventId

        override fun areContentsTheSame(old: EventUiModel, new: EventUiModel) =
            old == new
    }
}
