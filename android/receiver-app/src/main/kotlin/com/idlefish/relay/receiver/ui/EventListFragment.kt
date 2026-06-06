package com.idlefish.relay.receiver.ui

import android.os.Bundle
import android.view.View
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.idlefish.relay.receiver.R
import com.idlefish.relay.receiver.service.WebSocketService
import com.idlefish.relay.receiver.ui.adapter.EventAdapter
import kotlinx.coroutines.launch

class EventListFragment : Fragment(R.layout.fragment_event_list) {

    private var adapter: EventAdapter? = null

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val recyclerView = view.findViewById<RecyclerView>(R.id.event_list)
        val emptyHint = view.findViewById<TextView>(R.id.empty_hint)

        recyclerView.layoutManager = LinearLayoutManager(requireContext())

        adapter = EventAdapter { event ->
            (activity as? MainActivity)?.showDetail(event.eventId)
        }
        recyclerView.adapter = adapter

        val repository = WebSocketService.getRepository()
        lifecycleScope.launch {
            repository.eventsFlow.collect { events ->
                adapter?.submitList(events)
                if (events.isEmpty()) {
                    emptyHint.visibility = View.VISIBLE
                    recyclerView.visibility = View.GONE
                } else {
                    emptyHint.visibility = View.GONE
                    recyclerView.visibility = View.VISIBLE
                }
            }
        }
    }
}
