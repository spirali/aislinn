
/*--------------------------------------------------------------------*/
/*--- Aislinn                                                      ---*/
/*--------------------------------------------------------------------*/

/*
   This file is part of Aislinn

   Copyright (C) 2014 Stanislav Bohm

   This program is free software; you can redistribute it and/or
   modify it under the terms of the GNU General Public License as
   published by the Free Software Foundation; either version 2 of the
   License, or (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
   02111-1307, USA.

   The GNU General Public License is contained in the file COPYING.
*/

#include "pub_tool_basics.h"
#include "pub_tool_tooliface.h"
#include "pub_tool_libcassert.h"
#include "pub_tool_oset.h"
#include "pub_tool_libcprint.h"
#include "pub_tool_debuginfo.h"
#include "pub_tool_libcbase.h"
#include "pub_tool_options.h"
#include "pub_tool_basics.h"
#include "pub_tool_threadstate.h"
#include "pub_tool_mallocfree.h"
#include "pub_tool_hashtable.h"
#include "pub_tool_xarray.h"
#include "pub_tool_debuginfo.h"
#include "pub_tool_stacktrace.h"
#include "pub_tool_replacemalloc.h"

#include "../../include/aislinn.h"
#include "md5/md5.h"

/* Here, the internals of valgring are exponsed
 * But aislinn cannot work without it.
 * Some sufficient public interface should be
 * made in the future */
#include "../coregrind/pub_core_threadstate.h"
#include "../coregrind/pub_core_libcfile.h"


#define INLINE    inline __attribute__((always_inline))

#define SM_SIZE 65536            /* DO NOT CHANGE */
#define SM_MASK (SM_SIZE-1)      /* DO NOT CHANGE */

//#define SM_CHUNKS 16384
#define SM_CHUNKS 65536
#define SM_OFF(a) ((a) & SM_MASK)

typedef
   struct {
      UChar vabits8[SM_CHUNKS];
   }
   SecMap;

typedef
   struct {
      Addr    base;
      SecMap* sm;
   }
   AuxMapEnt;

typedef
   enum {
      BLOCK_FREE,
      BLOCK_USED,
      BLOCK_END
   } AllocationBlockType;

typedef
   struct {
      Addr address;
      AllocationBlockType type;
   } AllocationBlock;

typedef
   struct {
      OSet* auxmap;
      Addr heap_space;
      XArray *allocation_blocks;
   } MemorySpace;

typedef
   struct {
      Addr base;
      SecMap sm;
      UChar data[SM_SIZE];
   } MemoryImagePart;


typedef
   struct {
      MemoryImagePart *parts;
      UWord parts_size;
      XArray *allocation_blocks;
   } MemoryImage;

typedef
   // First two entries has to correspond to VgHashNode
   struct {
      struct State *next;
      UWord id;
      MemoryImage memimage;
      ThreadState threadstate;
   } State;

static int verbosity_level = 0;
static UWord heap_max_size = 128 * 1024 * 1024; // Default: 128M

static MemorySpace *current_memspace = NULL;
static VgHashTable states_table;

static Int control_socket = -1;

#define MAX_MESSAGE_BUFFER_LENGTH 20000
char message_buffer[MAX_MESSAGE_BUFFER_LENGTH];
Int message_buffer_size = 0;

Int server_port = -1;

/*static struct {
   UWord number_of_states;
} stats;*/

typedef
   enum {
      CET_FINISH,
      CET_CALL,
      CET_REPORT,
   } CommandsEnterType;

static void write_message(const char *str);
static void process_commands(CommandsEnterType cet);

/* --------------------------------------------------------
 *  Helpers
 * --------------------------------------------------------*/

static INLINE UWord make_new_id(void) {
   static UWord unique_id_counter = 100;
   return unique_id_counter++;
}

static INLINE Addr start_of_this_sm ( Addr a ) {
   return (a & (~SM_MASK));
}
static INLINE Bool is_start_of_sm ( Addr a ) {
   return (start_of_this_sm(a) == a);
}

/* --------------------------------------------------------
 *  Reports
 * --------------------------------------------------------*/

static void report_error(const char *code)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH, "REPORT %s\n", code);
   write_message(message);
   process_commands(CET_REPORT);
}


/* --------------------------------------------------------
 *  Memory managment
 * --------------------------------------------------------*/

static void memspace_init(void)
{
   /* It should be allocated with mmap with PROT_NONE to just reserse address space,
    * and change protection as necessary.
    * but I am not sure how to do it in valgrind libc in a way that address space is
    * placed into clients arena */
   Addr heap_space = (Addr) VG_(cli_malloc)(SM_SIZE, heap_max_size);
   tl_assert(heap_space != 0);

   MemorySpace *ms = VG_(malloc)("an.memspace", sizeof(MemorySpace));
   ms->auxmap = VG_(OSetGen_Create)(/*keyOff*/  offsetof(AuxMapEnt,base),
                                    /*fastCmp*/ NULL,
                                    VG_(malloc), "an.auxmap", VG_(free));
   ms->heap_space = heap_space;
   ms->allocation_blocks = VG_(newXA)
      (VG_(malloc), "an.allocations", VG_(free), sizeof(AllocationBlock));
   AllocationBlock block;
   block.address = heap_space;
   block.type = BLOCK_END;
   VG_(addToXA)(ms->allocation_blocks, &block);
   tl_assert(current_memspace == NULL);
   current_memspace = ms;
}

/*
static
void memspace_dump(void)
{
   VG_(printf)("========== MEMSPACE DUMP ===========\n");
   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
	   Word i;
	for (i = 0; i < SM_SIZE; i++) {
	      if (elem->sm->vabits8[i]) {
		      break;
	      }
	   }
      VG_(printf)("Auxmap %lu-%lu %lu\n", elem->base, elem->base + SM_SIZE, elem->base + i);
   }

   XArray *a = current_memspace->allocation_blocks;
   Word i;
   for (i = 0; i < VG_(sizeXA)(a); i++) {
       AllocationBlock *block = VG_(indexXA)(a, i);
       VG_(printf)("%lu: addr=%lu type=%d\n", i, block->address, block->type);
   }
}*/

static
Addr memspace_alloc(SizeT alloc_size)
{
   if (UNLIKELY(alloc_size == 0)) {
      alloc_size = 1;
   }
   // allign size
   alloc_size = (((alloc_size - 1) / sizeof(void*)) + 1) * sizeof(void*);

   XArray *a = current_memspace->allocation_blocks;
   Word i = 0;
   AllocationBlock *block = VG_(indexXA)(a, 0);
   AllocationBlock *next;
   while (block->type != BLOCK_END) {
      next = VG_(indexXA)(a, i + 1);
      if (block->type == BLOCK_FREE) {
         Word s = next->address - block->address;
         if (s >= alloc_size) {
            Word diff = s - alloc_size;
            block->type = BLOCK_USED;
            Addr address = block->address;
            if (diff > 0) {
               AllocationBlock new_block;
               new_block.type = BLOCK_FREE;
               new_block.address = address + alloc_size;
               VG_(insertIndexXA)(a, i + 1, &new_block);
            }
            return address;
         }
      }
      block = next;
      i++;
   }


   // No sufficient block found, create a new one
   Addr address = block->address;
   block->type = BLOCK_USED;
   AllocationBlock new_block;
   new_block.type = BLOCK_END;
   new_block.address = address + alloc_size;

   if (new_block.address - current_memspace->heap_space >= heap_max_size) {
      report_error("heaperror");
      tl_assert(0);
   }

   VG_(addToXA)(a, &new_block);
   return address;
}

static
SizeT memspace_free(Addr address)
{
    // TODO: replace by bisect search, array is sorted by address
    XArray *a = current_memspace->allocation_blocks;
    Word i, s = VG_(sizeXA)(a);
    AllocationBlock *block = NULL, *next, *prev;
    for (i = 0; i < s; i++) {
        block = VG_(indexXA)(a, i);
        if (block->address == address) {
            break;
        }
    }
    tl_assert(block && block->type == BLOCK_USED);
    block->type = BLOCK_FREE;
    next = VG_(indexXA)(a, i + 1);
    SizeT size = next->address - address;
    if (next->type == BLOCK_FREE) {
        VG_(removeIndexXA)(a, i + 1);
    }
    if (i > 0) {
        prev = VG_(indexXA)(a, i - 1);
        if (prev->type == BLOCK_FREE) {
            VG_(removeIndexXA)(a, i);
        }
    }
    return size;
}

static INLINE AuxMapEnt* maybe_find_in_auxmap ( Addr a )
{
   AuxMapEnt  key;
   AuxMapEnt* res;

   //tl_assert(a > MAX_PRIMARY_ADDRESS);
   a &= ~(Addr) SM_MASK;

   /* First search the front-cache, which is a self-organising
      list containing the most popular entries. */

  /* if (LIKELY(auxmap_L1[0].base == a))
      return auxmap_L1[0].ent;
   if (LIKELY(auxmap_L1[1].base == a)) {
      Addr       t_base = auxmap_L1[0].base;
      AuxMapEnt* t_ent  = auxmap_L1[0].ent;
      auxmap_L1[0].base = auxmap_L1[1].base;
      auxmap_L1[0].ent  = auxmap_L1[1].ent;
      auxmap_L1[1].base = t_base;
      auxmap_L1[1].ent  = t_ent;
      return auxmap_L1[0].ent;
   }

   n_auxmap_L1_searches++;

   for (i = 0; i < N_AUXMAP_L1; i++) {
      if (auxmap_L1[i].base == a) {
         break;
      }
   }
   tl_assert(i >= 0 && i <= N_AUXMAP_L1);

   n_auxmap_L1_cmps += (ULong)(i+1);

   if (i < N_AUXMAP_L1) {
      if (i > 0) {
         Addr       t_base = auxmap_L1[i-1].base;
         AuxMapEnt* t_ent  = auxmap_L1[i-1].ent;
         auxmap_L1[i-1].base = auxmap_L1[i-0].base;
         auxmap_L1[i-1].ent  = auxmap_L1[i-0].ent;
         auxmap_L1[i-0].base = t_base;
         auxmap_L1[i-0].ent  = t_ent;
         i--;
      }
      return auxmap_L1[i].ent;
   }

   n_auxmap_L2_searches++; */

   /* First see if we already have it. */
   key.base = a;
   key.sm   = 0;

   res = VG_(OSetGen_Lookup)(current_memspace->auxmap, &key);
   /*if (res)
      insert_into_auxmap_L1_at( AUXMAP_L1_INSERT_IX, res );*/
   return res;
}

static AuxMapEnt* find_or_alloc_in_auxmap (Addr a)
{
   AuxMapEnt *nyu, *res;

   /* First see if we already have it. */
   res = maybe_find_in_auxmap( a );
   if (LIKELY(res))
      return res;

   /* Ok, there's no entry in the secondary map, so we'll have
      to allocate one. */
   a &= ~(Addr) SM_MASK;

   nyu = (AuxMapEnt*) VG_(OSetGen_AllocNode)(
      current_memspace->auxmap, sizeof(AuxMapEnt) );
   tl_assert(nyu);
   nyu->base = a;
   nyu->sm = VG_(malloc)("an.secmap", sizeof(SecMap));
   VG_(memset(nyu->sm, 0, sizeof(SecMap)));
   //nyu->sm   = &sm_distinguished[SM_DIST_NOACCESS];
   VG_(OSetGen_Insert)(current_memspace->auxmap, nyu );
   /*insert_into_auxmap_L1_at( AUXMAP_L1_INSERT_IX, nyu );
   n_auxmap_L2_nodes++;*/
   return nyu;
}


static INLINE SecMap** get_secmap_high_ptr (Addr a)
{
   AuxMapEnt* am = find_or_alloc_in_auxmap(a);
   return &am->sm;
}

static INLINE SecMap** get_secmap_ptr (Addr a)
{
   /*return ( a <= MAX_PRIMARY_ADDRESS
          ? get_secmap_low_ptr(a)
          : get_secmap_high_ptr(a));*/
   return get_secmap_high_ptr(a);
}

static
void set_address_range_perms (
                Addr a, SizeT lenT, UChar perm)
{
   SecMap** sm_ptr;
   UWord    sm_off;

   UWord aNext = start_of_this_sm(a) + SM_SIZE;
   UWord len_to_next_secmap = aNext - a;
   UWord lenA, lenB;

   // lenT = lenA + lenB (lenA upto first sm, lenB is rest)
   if ( lenT <= len_to_next_secmap ) {
      lenA = lenT;
      lenB = 0;
   } else if (is_start_of_sm(a)) {
      lenA = 0;
      lenB = lenT;
      goto part2;
   } else {
      lenA = len_to_next_secmap;
      lenB = lenT - lenA;
   }

   sm_ptr = get_secmap_ptr(a);

   sm_off = SM_OFF(a);
   while (lenA > 0) {
      (*sm_ptr)->vabits8[sm_off] = perm;
      sm_off++;
      lenA--;
   }

   a = start_of_this_sm (a) + SM_SIZE;

part2:
   while (lenB >= SM_SIZE) {
      sm_ptr = get_secmap_ptr(a);
      VG_(memset)(&((*sm_ptr)->vabits8), perm, SM_CHUNKS);
      lenB -= SM_SIZE;
      a += SM_SIZE;
   }

   tl_assert(lenB < SM_SIZE);

   sm_ptr = get_secmap_ptr(a);
   sm_off = 0;
   while (lenB > 0) {
      (*sm_ptr)->vabits8[sm_off] = perm;
      sm_off++;
      lenB--;
   }
}

static INLINE void make_mem_undefined(Addr a, SizeT len)
{
   set_address_range_perms(a, len, 1);
}

static INLINE void make_mem_defined(Addr a, SizeT len)
{
   set_address_range_perms(a, len, 1);
}

static INLINE void make_mem_noaccess(Addr a, SizeT len)
{
   set_address_range_perms(a, len, 0);
}

static void secmap_hash_content(AN_(MD5_CTX) *ctx, Addr base, SecMap *sm)
{
   UWord i;
   /*for (i = 0; i < SM_SIZE; i++) {
      if (sm->vabits8[i]) {
	      VG_(printf)("First %lu %lu", i, base + i);
	      break;
      }
   }*/

   UChar *d = (UChar*) base;
   for (i = 0; i < SM_SIZE; i++) {
      if (sm->vabits8[i]) {
         AN_(MD5_Update)(ctx, &d[i], 1);
      }
   }
}

static void memimage_part_save_content(Addr base, SecMap *sm, MemoryImagePart *mpart)
{
   mpart->base = base;
   VG_(memcpy)(&mpart->sm, sm, sizeof(SecMap));

   UWord i;
   UChar *d = (UChar*) base;
   UWord c = 0;
   UChar *data = &mpart->data[0];
   for (i = 0; i < SM_SIZE; i++) {
      if (sm->vabits8[i]) {
         data[i] = d[i];
         c++;
      }
   }
}

static void memimage_part_restore_content(MemoryImagePart *mpart)
{
   UWord i;
   UChar *d = (UChar*) mpart->base;
   SecMap *sm = &mpart->sm;
   UChar *data = &mpart->data[0];
   for (i = 0; i < SM_SIZE; i++) {
      if (sm->vabits8[i]) {
          d[i] = data[i];
      }
   }
}

static void memimage_save_current(MemoryImage *memimage)
{
   Word size = VG_(OSetGen_Size)(current_memspace->auxmap);
   memimage->parts_size = size;
   MemoryImagePart *mpart = VG_(malloc)("an.memimage", size * sizeof(MemoryImagePart));
   memimage->parts = mpart;

   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      memimage_part_save_content(elem->base, elem->sm, mpart);
      mpart++;
   }
   memimage->allocation_blocks = VG_(cloneXA)("an.memimage",
                                              current_memspace->allocation_blocks);
}

static void memimage_free(MemoryImage *memimage)
{
   VG_(free)(memimage->parts);
   VG_(deleteXA)(memimage->allocation_blocks);
}

static void memimage_restore_current(MemoryImage *memimage)
{
   OSet *auxmap = VG_(OSetGen_EmptyClone)(current_memspace->auxmap);
   VG_(OSetGen_Destroy(current_memspace->auxmap));
   current_memspace->auxmap = auxmap;

   UWord i;
   for (i = 0; i < memimage->parts_size; i++) {
      MemoryImagePart *mpart = &memimage->parts[i];
      AuxMapEnt *nyu;
      nyu = (AuxMapEnt*) VG_(OSetGen_AllocNode)(auxmap, sizeof(AuxMapEnt));
      nyu->base = mpart->base;
      memimage_part_restore_content(mpart);
      nyu->sm = VG_(malloc)("an.secmap", sizeof(SecMap));
      VG_(memcpy)(nyu->sm, &mpart->sm, sizeof(SecMap));
      VG_(OSetGen_Insert)(auxmap, nyu);
   }

   VG_(deleteXA)(current_memspace->allocation_blocks);
   current_memspace->allocation_blocks = VG_(cloneXA)("an.allocations",
                                                      memimage->allocation_blocks);
}

static void memspace_hash(AN_(MD5_CTX) *ctx)
{
   //memspace_dump();
   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      AN_(MD5_Update)(ctx, elem->sm, sizeof(SecMap));
      //VG_(printf)("Updating secmap %lu\n", elem->base);
      secmap_hash_content(ctx, elem->base, elem->sm);
   }
}

/* --------------------------------------------------------
 *  Buffer management
 * --------------------------------------------------------*/

static void* buffer_new(void* addr, UWord size)
{
   UWord *buffer = VG_(malloc)("an.buffers", sizeof(UWord) + size);
   *buffer = size;
   VG_(memcpy)(buffer + 1, addr, size);
   return buffer;
}

static void buffer_free(void *addr)
{
   VG_(free)(addr);
}

static void buffer_hash(void *addr, AN_(MD5_CTX) *ctx)
{
   UWord *buffer = addr;
   AN_(MD5_Update)(ctx, addr, sizeof(UWord) + *buffer);
}

/* --------------------------------------------------------
 *  State management
 * --------------------------------------------------------*/

static State* state_save_current(void)
{
   State *state = VG_(malloc)("an.state", sizeof(State));
   VG_(memset)(state, 0, sizeof(State));
   state->id = make_new_id();

   /* Save thread state */
   ThreadId tid = VG_(get_running_tid());
   tl_assert(tid == 1); // No forking supported yet
   ThreadState *tst = VG_(get_ThreadState)(tid);
   tl_assert(tst);
   tl_assert(tst->status != VgTs_Empty);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
   VG_(memcpy)(&state->threadstate, tst, sizeof(ThreadState));

   /* Save memory state */
   memimage_save_current(&state->memimage);

   return state;
}

static void state_free(State *state)
{
   memimage_free(&state->memimage);
   VG_(free)(state);
}

static void state_hash(AN_(MD5_CTX) *ctx)
{
   ThreadId tid = VG_(get_running_tid());
   tl_assert(tid == 1);
   ThreadState *tst = VG_(get_ThreadState)(tid);

   tl_assert(tst);
   tl_assert(tst->status != VgTs_Empty);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue

   SizeT size = sizeof(ThreadArchState);
   // Do not hash EvC_COUNTER and start from first register
   size -= offsetof(VexGuestArchState, guest_RAX);
   AN_(MD5_Update)(ctx, &tst->arch.vex.guest_RAX, size);

   memspace_hash(ctx);
}

static void state_restore(State *state)
{
   /* Restore thread */
   ThreadState *tst = VG_(get_ThreadState)(1);
   tl_assert(tst);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue

   //tst->arch.vex.guest_RDX = 0; // Result of client request
   VG_(memcpy)(tst, &state->threadstate, sizeof(ThreadState));

   /* Restore memory image */
   memimage_restore_current(&state->memimage);
}

/* --------------------------------------------------------
 *  CONTROLL
 * --------------------------------------------------------*/

static Int connect_to_server(const HChar *server_addr)
{
   Int s;
   s = VG_(connect_via_socket(server_addr));

   if (s == -1) {
      VG_(fmsg)("Invalid server address '%s'\n", server_addr);
      VG_(exit)(1);
   }
   if (s == -2) {
      VG_(umsg)("failed to connect to server '%s'.\n", server_addr);
      VG_(exit)(1);
   }
   tl_assert(s > 0);
   return s;
}

static
Bool read_command(char *command)
{
   char *s = message_buffer;
   Int rest = MAX_MESSAGE_BUFFER_LENGTH;
   Int len = message_buffer_size;
   Int total_len = 0;
   Int i;

   for(;;) {
      for (i = 0; i < len; i++) {
            if (*s == '\n') {
               goto ret;
            }
            s++;
      }

      total_len += len;
      rest -= len;
      tl_assert(rest > 0); // If fail, command was to long
      len = VG_(read_socket)(control_socket, s, rest);
      if (len == 0) {
         return False; // Connection closed
      }
   }

ret:
   VG_(memcpy(command, message_buffer, total_len + i));
   command[total_len + i] = 0;
   message_buffer_size = len - i - 1;
   VG_(memmove(message_buffer,
               message_buffer + total_len + i + 1,
               message_buffer_size));
   return True;
}

static void write_message(const char *str)
{
   if (verbosity_level > 0) {
      VG_(printf)("AN>> %s", str);
   }
   Int len = VG_(strlen)(str);
   Int r = VG_(write_socket)(control_socket, str, len);
   if (r == -1) {
      VG_(printf)("Connection closed\n");
      VG_(exit)(1);
   }
   tl_assert(r == len);
}

struct BufferCtrl {
   HChar *buffer;
   int size;
};

static void write_stacktrace_helper(UInt n, Addr ip, void *opaque)
{
   struct BufferCtrl *bc = opaque;
   VG_(describe_IP)(ip, bc->buffer, bc->size - 1);
   SizeT s = VG_(strlen)(bc->buffer);
   bc->buffer[s] = '|';
   s += 1;
   bc->buffer += s;
   bc->size -= s;
}

static void write_stacktrace(void)
{
   const int MAX_IPS = 16;
   Addr ips[MAX_IPS];
   UInt n_ips
      = VG_(get_StackTrace)(1 /* tid */, ips, MAX_IPS, // MAX DEB,
                            NULL/*array to dump SP values in*/,
                            NULL/*array to dump FP values in*/,
                            0/*first_ip_delta*/);
  struct BufferCtrl bc;
  HChar buffer[MAX_MESSAGE_BUFFER_LENGTH];
  bc.buffer = buffer;
  bc.size = MAX_MESSAGE_BUFFER_LENGTH - 1;
  VG_(apply_StackTrace)(write_stacktrace_helper, &bc, ips, n_ips );
  *(bc.buffer - 1) = '\n';
  *(bc.buffer) = '\0';
  write_message(buffer);
}

static const char hex_chars[16] = {
        '0', '1', '2', '3', '4', '5', '6', '7',
        '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'
};

/* Convert 16B MD5 hash digest to 32B human readable string
 * "out" has to be 33B length buffer, because functions add \0 */
static void hash_to_string(unsigned char *digest, char *out)
{
   int i = 0;
   for (i = 0; i < 16; ++i) {
      char Byte = digest[i];
      out[i*2] = hex_chars[(Byte & 0xF0) >> 4];
      out[i*2+1] = hex_chars[Byte & 0x0F];
   }
   out[32] = 0;
}

static char* next_token(void) {
   char *str = VG_(strtok)(NULL, " ");
   if (str == NULL) {
      write_message("Error: Invalid command\n");
      VG_(exit)(1);
   }
   return str;
}

static UWord next_token_uword(void) {
   char *str = next_token();
   char *end;
   UWord value = VG_(strtoull10)(str, &end);
   if (*end != '\0') {
      write_message("Error: Invalid argument\n");
      VG_(exit)(1);
   }
   return value;
}

static void process_commands_init(void) {
   ThreadState *tst = VG_(get_ThreadState)(1);
   tl_assert(tst);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
   tl_assert(!tst->sched_jmpbuf_valid);
   // Reset invalid jmpbuf to make be able generate reasonable hash of state
   //VG_(memset)(tst->sched_jmpbuf, 0, sizeof(tst->sched_jmpbuf));
   tst->arch.vex.guest_RDX = 0; // Result of client request
}

static
void process_commands(CommandsEnterType cet)
{
   process_commands_init();
   char command[MAX_MESSAGE_BUFFER_LENGTH + 1];

   for (;;) {
      if (!read_command(command)) {
         VG_(exit)(1);
      }
      if (verbosity_level > 0) {
        VG_(printf)("AN<< %s\n", command);
      }
      char *cmd = VG_(strtok(command, " "));

      if (!VG_(strcmp(cmd, "SAVE"))) {
         State *state = state_save_current();
         VG_(HT_add_node(states_table, state));
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH, "%lu\n", state->id));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp)(cmd, "RESTORE")) {
         UWord state_id = next_token_uword();

         State *state = (State*) VG_(HT_lookup(states_table, state_id));
         if (state == NULL) {
            write_message("Error: State not found\n");
         }
         state_restore(state);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp)(cmd, "WRITE")) {
         void *addr = (void*) next_token_uword();
         char *param = next_token();
         if (!VG_(strcmp)(param, "int")) {
            *((Int*) addr) = next_token_uword();
         } else if (!VG_(strcmp(param, "buffer"))) {
            UWord *buffer = (UWord*) next_token_uword();
            UWord size = *buffer;
            VG_(memcpy(addr, buffer + 1, size));
         } else {
            write_message("Error: Invalid argument\n");
            VG_(exit)(1);
         }
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp)(cmd, "READ")) {
         void *addr = (void*) next_token_uword();
         char *param = next_token();
         if (!VG_(strcmp)(param, "int")) {
            VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                         "%d\n", *((Int*) addr)));
         } else if(!VG_(strcmp)(param, "ints")) {
             UWord count = next_token_uword();
             UWord written = 0;
             UWord i;
             Int *iaddr = addr;
             for (i = 0; i < count; i++) {
                written += VG_(snprintf)(command + written,
                                         MAX_MESSAGE_BUFFER_LENGTH - written,
                                         "%d ", *iaddr);
                iaddr += 1;
             }
             written += VG_(snprintf)(command + written,
                                      MAX_MESSAGE_BUFFER_LENGTH - written,
                                      "\n");
             tl_assert(written < MAX_MESSAGE_BUFFER_LENGTH);
         } else {
            write_message("Error: Invalid argument\n");
            VG_(exit)(1);
         }
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "RUN"))) {
         if (UNLIKELY(cet == CET_REPORT)) {
            VG_(printf)("Process cannot be resume after report");
            VG_(exit)(1);
         }
         if (cet == CET_FINISH) { // Thread finished, so after restore, status has to be fixed
            ThreadState *tst = VG_(get_ThreadState)(1);
            tst->status = VgTs_Init;
         }
         return;
      }

      if (!VG_(strcmp(cmd, "NEW_BUFFER"))) { // Create buffer
         void* addr = (void*) next_token_uword();
         UWord size = next_token_uword();
         void* buffer = buffer_new(addr, size);
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%lu\n", (UWord) buffer));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "NEW_BUFFER_HASH"))) { // Create buffer
         void* addr = (void*) next_token_uword();
         UWord size = next_token_uword();
         void* buffer = buffer_new(addr, size);
         unsigned char digest[16];
         char digest_str[33]; // 16 * 2 + 1
         AN_(MD5_CTX) ctx;
         AN_(MD5_Init)(&ctx);
         buffer_hash(buffer, &ctx);
         AN_(MD5_Final)(digest, &ctx);
         hash_to_string(digest, digest_str);
         VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%lu %s\n", (UWord) buffer, digest_str);
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "FREE_BUFFER"))) { // free buffer
         void* addr = (void*) next_token_uword();
         buffer_free(addr);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "HASH"))) {
         unsigned char digest[16];
         char digest_str[33]; // 16 * 2 + 1
         AN_(MD5_CTX) ctx;
         AN_(MD5_Init)(&ctx);
         state_hash(&ctx);
         AN_(MD5_Final)(digest, &ctx);
         hash_to_string(digest, digest_str);
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%s\n", digest_str));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp)(cmd, "STACKTRACE")) {
         write_stacktrace();
         continue;
      }

      if (!VG_(strcmp)(cmd, "FREE")) {
         UWord state_id = next_token_uword();

         State *state = (State*) VG_(HT_lookup(states_table, state_id));
         if (state == NULL) {
            write_message("Error: State not found\n");
            VG_(exit)(1);
         }
         VG_(HT_remove)(states_table, state_id);
         state_free(state);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "QUIT"))) {
         VG_(exit)(1);
      }
      write_message("Error: Unknown command\n");
   }
}

/* --------------------------------------------------------
 *  CALLBACKS
 */

static
Bool an_handle_client_request ( ThreadId tid, UWord* arg, UWord* ret )
{
   tl_assert(tid == 1); // No multithreading supported yet

   if (!VG_IS_TOOL_USERREQ('A','N',arg[0])) {
        return False;
   }

   char message[MAX_MESSAGE_BUFFER_LENGTH + 1];
   tl_assert(arg[1]);
   switch(arg[0]) {
      case VG_USERREQ__AISLINN_CALL_0:
         VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                       "CALL %s\n", (char*) arg[1]);
         break;
      case VG_USERREQ__AISLINN_CALL_1:
         VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                       "CALL %s %lu\n", (char*) arg[1], arg[2]);
         break;
      case VG_USERREQ__AISLINN_CALL_2:
         VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                       "CALL %s %lu %lu\n",
                       (char*) arg[1], arg[2], arg[3]);
         break;
      case VG_USERREQ__AISLINN_CALL_3:
         VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                       "CALL %s %lu %lu %lu\n",
                       (char*) arg[1], arg[2], arg[3], arg[4]);
         break;
      case VG_USERREQ__AISLINN_CALL_4:
         VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                       "CALL %s %lu %lu %lu %lu\n",
                       (char*) arg[1], arg[2], arg[3], arg[4], arg[5]);
         break;
      case VG_USERREQ__AISLINN_CALL_ARGS: {
         Int l = MAX_MESSAGE_BUFFER_LENGTH - 1; // reserve 1 char for \n
         UWord i;
         char *m = message;
         Int p = VG_(snprintf)(m, l, "CALL %s", (char*) arg[1]);
         m += p;
         l -= p;
         UWord *a = (UWord*) arg[2];
         UWord a_count = arg[3];
         for (i = 0; i < a_count; i++) {
            p = VG_(snprintf)(m, l, " %lu", a[i]);
            m += p;
            l -= p;
         }
         VG_(strcpy)(m, "\n");
       } break;
      default:
         tl_assert(0);
   }

   write_message(message);
   process_commands(CET_CALL);
   return True;
}

static
void new_mem_mmap (Addr a, SizeT len, Bool rr, Bool ww, Bool xx,
                   ULong di_handle)
{
   //VG_(printf)("MMAP %lu-%lu %lu %d %d %d\n", a, a + len, len, rr, ww, xx);

   if (rr && ww) {
      make_mem_defined(a, len);
   } else {
      make_mem_noaccess(a, len);
   }
}

static
void new_mem_mprotect ( Addr a, SizeT len, Bool rr, Bool ww, Bool xx )
{
   //VG_(printf)("MPROTECT %lu-%lu %lu %d %d %d\n", a, a + len, len, rr, ww, xx);
   //
   if (rr && ww) {
      make_mem_defined(a, len);
   } else {
      make_mem_noaccess(a, len);
   }
}

static
void mem_unmap(Addr a, SizeT len)
{
   //VG_(printf)("UNMAP %lu-%lu %lu %d %d %d\n", a, a + len, len);
   make_mem_noaccess(a, len);
}

static
void copy_address_range_state ( Addr src, Addr dst, SizeT len )
{
   VG_(printf)("COPY_ADDRESS_RANGE_STATE: not implemented yet %lu", src);
   tl_assert(0);
}

static
void new_mem_startup(Addr a, SizeT len,
                     Bool rr, Bool ww, Bool xx, ULong di_handle)
{
   new_mem_mmap(a, len, rr, ww, xx, di_handle);
}

static void new_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("NEW STACK %p %lu\n", (void*) a, len);
   make_mem_undefined(a, len);
}

static void die_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("DIE STACK %p %lu\n", (void*) a, len);
   make_mem_noaccess(a, len);
}

static void an_post_clo_init(void)
{
   if (server_port == -1) {
      VG_(printf)("Server port was not specified\n");
      VG_(exit)(1);
   }
   if (server_port < 0 || server_port > 65535) {
      VG_(printf)("Invalid server port\n");
      VG_(exit)(1);
   }
   char target[300];
   VG_(snprintf)(target, 300, "127.0.0.1:%u", server_port);
   control_socket = connect_to_server(target);
   tl_assert(control_socket > 0);
}

static
Bool restore_thread(ThreadId tid)
{
   ThreadState *tst = VG_(get_ThreadState)(tid);
   char str[100];
   VG_(snprintf)(str, 100, "EXIT %lu\n", tst->os_state.exitcode);
   write_message(str);
   process_commands(CET_FINISH);
   return True;
}

static
IRSB* an_instrument ( VgCallbackClosure* closure,
                      IRSB* bb,
                      VexGuestLayout* layout,
                      VexGuestExtents* vge,
                      VexArchInfo* archinfo_host,
                      IRType gWordTy, IRType hWordTy )
{
    return bb;
}

static void an_fini(Int exitcode)
{
}

static Bool process_cmd_line_option(const HChar* arg)
{
   if (VG_INT_CLO(arg, "--port", server_port)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--verbose", verbosity_level)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--heapsize", heap_max_size)) {
      return True;
   }

   return False;
}

static void print_usage(void)
{

}

static void print_debug_usage(void)
{

}

static void* user_malloc (ThreadId tid, SizeT n)
{
   //memspace_dump();
    Addr addr = memspace_alloc(n);
    make_mem_undefined(addr, n);
    //VG_(printf)("!!! MALLOC %lu %lu\n", addr,  n);
    return (void*) addr;
}

static void user_free (ThreadId tid, void *a)
{
    //VG_(printf)("!!! FREE %p\n", a);
    SizeT size = memspace_free((Addr) a);
    make_mem_noaccess((Addr) a, size);
}

static void an_pre_clo_init(void)
{
   VG_(details_name)            ("Aislinn");
   VG_(details_version)         (NULL);
   VG_(details_description)     ("");
   VG_(details_copyright_author)(
      "Copyright (C) 2014, and GNU GPL'd, by Stanislav Bohm.");
   VG_(details_bug_reports_to)  (VG_BUGS_TO);

   VG_(details_avg_translation_sizeB) ( 275 );

   VG_(basic_tool_funcs)        (an_post_clo_init,
                                 an_instrument,
                                 an_fini);

   VG_(needs_restore_thread)(restore_thread);

   VG_(needs_command_line_options)(process_cmd_line_option,
                                   print_usage,
                                   print_debug_usage);

   VG_(needs_malloc_replacement)  (user_malloc,
                                   user_malloc, //MC_(__builtin_new),
                                   user_malloc, //MC_(__builtin_vec_new),
                                   NULL, //MC_(memalign),
                                   NULL, //MC_(calloc),
                                   user_free, //MC_(free),
                                   NULL, //MC_(__builtin_delete),
                                   NULL, //MC_(__builtin_vec_delete),
                                   NULL, //MC_(realloc),
                                   NULL, //MC_(malloc_usable_size),
                                   0);
   VG_(track_new_mem_startup) (new_mem_startup);
   VG_(track_change_mem_mprotect) (new_mem_mprotect);

   VG_(track_copy_mem_remap)      (copy_address_range_state);
   VG_(track_die_mem_stack_signal)(mem_unmap);
   VG_(track_die_mem_brk)         (mem_unmap);
   VG_(track_die_mem_munmap)      (mem_unmap);

   /*VG_(track_new_mem_mmap)    (an_new_mem_mmap);
   VG_(track_new_mem_brk)     (an_new_mem_brk);
   VG_(needs_client_requests) (an_handle_client_request);

   VG_(needs_restore_thread)(an_restore_thread);*/

   VG_(track_new_mem_stack) (new_mem_stack);
   VG_(track_die_mem_stack) (die_mem_stack);
   VG_(needs_client_requests) (an_handle_client_request);

   states_table = VG_(HT_construct)("an.states");

   memspace_init();
}

VG_DETERMINE_INTERFACE_VERSION(an_pre_clo_init)

/*--------------------------------------------------------------------*/
/*--- end                                                          ---*/
/*--------------------------------------------------------------------*/
