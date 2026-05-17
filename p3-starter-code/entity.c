/******************************************************************************/
/*                                                                            */
/* ENTITY IMPLEMENTATIONS                                                     */
/*                                                                            */
/******************************************************************************/

#include <stdio.h>
#include <string.h>
#include "simulator.h"

#define MAX_BUF  1000
#define TIMEOUT  20.0f

/* -------------------------------------------------------------------------- */
/* Shared helpers (pure functions — no global state, safe to call from A or B)*/
/* -------------------------------------------------------------------------- */

static int compute_checksum(struct pkt *p) {
    int sum = p->seqnum + p->acknum + p->length;
    int len = (p->length >= 0 && p->length <= 32) ? p->length : 0;
    for (int i = 0; i < len; i++)
        sum += (unsigned char)p->payload[i];
    return sum;
}

static int is_corrupt(struct pkt *p) {
    return compute_checksum(p) != p->checksum;
}

/* -------------------------------------------------------------------------- */
/* A ENTITY — Go-Back-N sender                                                */
/* -------------------------------------------------------------------------- */

static int   a_window_size;
static int   a_base;       /* seq# of oldest unACKed packet          */
static int   a_next_seq;   /* seq# of next packet to create and send */

/* Circular window buffer: stores every packet sent but not yet ACKed.
   Indexed by seqnum % MAX_BUF.  Safe as long as window_size <= MAX_BUF. */
static struct pkt a_sent_pkts[MAX_BUF];

/* FIFO queue of messages that arrived while the window was full. */
static struct msg a_msg_queue[MAX_BUF];
static int a_queue_head;   /* index of front element            */
static int a_queue_tail;   /* index one past the last element   */
static int a_queue_size;

static struct pkt a_make_pkt(int seq, struct msg *m) {
    struct pkt p;
    p.seqnum  = seq;
    p.acknum  = 0;
    p.length  = m->length;
    memcpy(p.payload, m->data, m->length);
    p.checksum = compute_checksum(&p);
    return p;
}

/* Send as many queued messages as the window now allows. */
static void a_flush_queue(void) {
    while (a_queue_size > 0 && (a_next_seq - a_base) < a_window_size) {
        struct msg m = a_msg_queue[a_queue_head];
        a_queue_head = (a_queue_head + 1) % MAX_BUF;
        a_queue_size--;

        struct pkt p = a_make_pkt(a_next_seq, &m);
        a_sent_pkts[a_next_seq % MAX_BUF] = p;

        /* Start the timer on the first packet that opens the window. */
        if (a_next_seq == a_base)
            starttimer_A(TIMEOUT);

        tolayer3_A(p);
        a_next_seq++;
    }
}

void A_init(int window_size) {
    a_window_size = window_size;
    a_base        = 0;
    a_next_seq    = 0;
    a_queue_head  = 0;
    a_queue_tail  = 0;
    a_queue_size  = 0;
}

void A_output(struct msg message) {
    if ((a_next_seq - a_base) < a_window_size) {
        /* Window has room — send immediately. */
        struct pkt p = a_make_pkt(a_next_seq, &message);
        a_sent_pkts[a_next_seq % MAX_BUF] = p;

        /* Timer only needed when the first in-flight packet is created. */
        if (a_next_seq == a_base)
            starttimer_A(TIMEOUT);

        tolayer3_A(p);
        a_next_seq++;
    } else {
        /* Window full — queue for later. */
        if (a_queue_size >= MAX_BUF) {
            printf("[A] message queue full — dropping message\n");
            return;
        }
        a_msg_queue[a_queue_tail] = message;
        a_queue_tail = (a_queue_tail + 1) % MAX_BUF;
        a_queue_size++;
    }
}

void A_input(struct pkt packet) {
    if (is_corrupt(&packet))
        return;

    int ack = packet.acknum;

    /* Ignore ACKs outside the current window (duplicates from past windows). */
    if (ack < a_base || ack >= a_next_seq)
        return;

    /* Cumulative ACK: slide base forward. */
    a_base = ack + 1;

    stoptimer_A();
    if (a_base < a_next_seq)
        starttimer_A(TIMEOUT);

    /* Opportunity to send any queued messages. */
    a_flush_queue();
}

void A_timerinterrupt() {
    /* Retransmit every unACKed packet in the current window. */
    starttimer_A(TIMEOUT);
    for (int seq = a_base; seq < a_next_seq; seq++)
        tolayer3_A(a_sent_pkts[seq % MAX_BUF]);
}

/* -------------------------------------------------------------------------- */
/* B ENTITY — Go-Back-N receiver                                              */
/* -------------------------------------------------------------------------- */

static int b_expected_seq;
static int b_last_ack;     /* seq# of last in-order packet delivered (-1 = none) */

static struct pkt b_make_ack(int acknum) {
    struct pkt p;
    p.seqnum   = 0;
    p.acknum   = acknum;
    p.length   = 0;
    memset(p.payload, 0, 32);
    p.checksum = compute_checksum(&p);
    return p;
}

void B_init(int window_size) {
    b_expected_seq = 0;
    b_last_ack     = -1;
}

void B_input(struct pkt packet) {
    if (is_corrupt(&packet)) {
        /* Re-ACK last good packet so A can slide its window on duplicate ACKs. */
        if (b_last_ack >= 0)
            tolayer3_B(b_make_ack(b_last_ack));
        return;
    }

    if (packet.seqnum == b_expected_seq) {
        /* Deliver in-order packet to layer 5. */
        struct msg m;
        m.length = packet.length;
        memcpy(m.data, packet.payload, packet.length);
        tolayer5_B(m);

        b_last_ack = b_expected_seq;
        b_expected_seq++;

        tolayer3_B(b_make_ack(b_last_ack));
    } else {
        /* Out-of-order — GBN discards and re-ACKs the last good seq#. */
        if (b_last_ack >= 0)
            tolayer3_B(b_make_ack(b_last_ack));
    }
}

void B_timerinterrupt() {
    /* B does not use its timer in this implementation. */
}
