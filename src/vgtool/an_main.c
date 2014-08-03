
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
#include "pub_tool_machine.h"     // VG_(fnptr_to_fnentry)
#include "../../include/aislinn.h"
#include "md5/md5.h"

/* Here, the internals of valgring are exponsed
 * But aislinn cannot work without it.
 * Some sufficient public interface should be
 * made in the future */
#include "../coregrind/pub_core_threadstate.h"
#include "../coregrind/pub_core_libcfile.h"


#define INLINE    inline __attribute__((always_inline))

#define VPRINT(level, ...) if (verbosity_level >= (level)) { VG_(printf)(__VA_ARGS__); }

#define PAGE_SIZE 65536            /* DO NOT CHANGE */
#define PAGE_MASK (PAGE_SIZE-1)      /* DO NOT CHANGE */

//#define VA_CHUNKS 16384
#define VA_CHUNKS 65536
#define PAGE_OFF(a) ((a) & PAGE_MASK)

typedef
   struct {
      UChar vabits[VA_CHUNKS];
   } VA;

typedef
   struct {
      Addr base;
      Int ref_count;
      VA *va;
      UChar *data;
      Bool has_hash;
      MD5_Digest hash;
   } Page;

typedef
   struct {
      Addr    base;
      Page* page;
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
      Page **pages;
      UWord pages_count;
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

static struct {
   Word pages; // Number of currently allocated pages
} stats;

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

static INLINE Addr start_of_this_page ( Addr a ) {
   return (a & (~PAGE_MASK));
}

static INLINE Bool is_start_of_page ( Addr a ) {
   return (start_of_this_page(a) == a);
}

/*static INLINE Bool is_distinguished_sm (SecMap* sm) {
   return sm >= &sm_distinguished[0] && sm <= &sm_distinguished[1];
}*/

/* --------------------------------------------------------
 *  Reports
 * --------------------------------------------------------*/

static NOINLINE void report_error(const char *code)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH, "REPORT %s\n", code);
   write_message(message);
   process_commands(CET_REPORT);
   tl_assert(0); // no return from process_commands
}

static NOINLINE void report_error_write(Addr addr, SizeT size)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH, "invalidwrite %lx %lu", addr, size);
   report_error(message);
}


/* --------------------------------------------------------
 *  Memory managment
 * --------------------------------------------------------*/

static void memspace_init(void)
{
   /* Here we need to reserve an address space for our heap manager,
    * We need deterministic allocator that can be saved into and restored from memimage
    *
    * VG_(malloc) is not good solution because address is taken from a bad memory area and optimization
    * like in memcheck (primary map) cannot be applied
    * But VG_(cli_malloc) is not used because it reports underlying mmap
    * through new_mem_mmap and it causes that the whole heap space would be marked through VA flags.
    * ?? Probably VG_(am_mmap_anon_float_client) should be called
    */
   Addr heap_space = (Addr) VG_(malloc)("heap", heap_max_size);


   tl_assert(heap_space != 0);
   VPRINT(2, "memspace_init: heap %lu-%lu\n", heap_space, heap_space + heap_max_size);

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


/*static
void memspace_dump(void)
{
   VG_(printf)("========== MEMSPACE DUMP ===========\n");
   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      VG_(printf)("Auxmap %lu-%lu %d %lu\n", elem->base, elem->base + PAGE_SIZE, elem->ref_count, (Addr) elem->data);
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
   a &= ~(Addr) PAGE_MASK;

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

   res = VG_(OSetGen_Lookup)(current_memspace->auxmap, &key);
   /*if (res)
      insert_into_auxmap_L1_at( AUXMAP_L1_INSERT_IX, res );*/
   return res;
}

static Page *page_new(Addr a)
{
    stats.pages++;

    Page *page = (Page*) VG_(malloc)("an.page", sizeof(Page));
    page->base = a;
    page->ref_count = 1;
    page->has_hash = False;
    page->data = NULL;
    page->va = VG_(malloc)("an.va", sizeof(VA));
    VPRINT(2, "page_new base=%lu %p\n", a, page);
    return page;
}

// Page is cloned without data and hash
static Page* page_clone(Page *page)
{
   Page *new_page = page_new(page->base);
   VG_(memcpy)(new_page->va, page->va, sizeof(VA));
   return new_page;
}

static void page_dispose(Page *page)
{
   page->ref_count--;
   if (page->ref_count <= 0) {
      tl_assert(page->ref_count == 0);
      stats.pages--;
      if (page->data) {
         VG_(free)(page->data);
      }
      VG_(free)(page->va);
      VG_(free)(page);
   }
}

static AuxMapEnt* find_or_alloc_in_auxmap (Addr a)
{   
   AuxMapEnt *nyu, *res;
   Page *page;

   /* First see if we already have it. */
   res = maybe_find_in_auxmap( a );
   if (LIKELY(res))
      return res;

   /* Ok, there's no entry in the secondary map, so we'll have
      to allocate one. */
   a &= ~(Addr) PAGE_MASK;

   nyu = (AuxMapEnt*) VG_(OSetGen_AllocNode)(
      current_memspace->auxmap, sizeof(AuxMapEnt));
   tl_assert(nyu);
   nyu->base = a;
   page = page_new(a);
   nyu->page = page;
   //nyu->sm = &sm_distinguished[SM_DIST_NOACCESS];
   /*nyu->sm = VG_(malloc)("an.secmap", sizeof(SecMap));
   VG_(memset(nyu->sm, 0, sizeof(SecMap)));*/
   VG_(OSetGen_Insert)(current_memspace->auxmap, nyu);
   /*insert_into_auxmap_L1_at( AUXMAP_L1_INSERT_IX, nyu );
   n_auxmap_L2_nodes++;*/
   return nyu;
}

static void INLINE make_own_copy_of_page(Page **page) {
   VPRINT(2, "make_own_copy base=%lu refcount=%d page=%p\n", (*page)->base, (*page)->ref_count, (*page));
   if (UNLIKELY((*page)->ref_count >= 2)) {
      (*page)->ref_count--;
      Page *new_page = page_clone(*page);
      *page = new_page;
   } else {
    (*page)->has_hash = False;
   }
}


static void INLINE page_prepare_for_va_write(Page **page) {
   make_own_copy_of_page(page);
}

static INLINE Page** get_page_ptr (Addr a)
{
   /*return ( a <= MAX_PRIMARY_ADDRESS
          ? get_secmap_low_ptr(a)
          : get_secmap_high_ptr(a));*/
   //return get_secmap_high_ptr(a);
   return &find_or_alloc_in_auxmap(a)->page;
}

static
void set_address_range_perms (
                Addr a, SizeT lenT, UChar perm)
{  
   VA* va;
   Page **page_ptr;
   UWord pg_off;

   UWord aNext = start_of_this_page(a) + PAGE_SIZE;
   UWord len_to_next_secmap = aNext - a;
   UWord lenA, lenB;

   // lenT = lenA + lenB (lenA upto first page, lenB is rest)
   if (is_start_of_page(a)) {
      lenA = 0;
      lenB = lenT;
      goto part2;
   } else if ( lenT <= len_to_next_secmap ) {
      lenA = lenT;
      lenB = 0;
   } else {
      lenA = len_to_next_secmap;
      lenB = lenT - lenA;
   }

   page_ptr = get_page_ptr(a);
   page_prepare_for_va_write(page_ptr);
   va = (*page_ptr)->va;
   pg_off = PAGE_OFF(a);
   while (lenA > 0) {
      va->vabits[pg_off] = perm;
      pg_off++;
      lenA--;
   }

   a = start_of_this_page (a) + PAGE_SIZE;

part2:
   while (lenB >= PAGE_SIZE) {
      page_ptr = get_page_ptr(a);
      page_prepare_for_va_write(page_ptr);
      va = (*page_ptr)->va;

      VG_(memset)(&((va)->vabits), perm, VA_CHUNKS);
      lenB -= PAGE_SIZE;
      a += PAGE_SIZE;
   }

   tl_assert(lenB < PAGE_SIZE);

   page_ptr = get_page_ptr(a);
   page_prepare_for_va_write(page_ptr);
   va = (*page_ptr)->va;
   pg_off = 0;
   while (lenB > 0) {
      va->vabits[pg_off] = perm;
      pg_off++;
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

static void hash_to_string(MD5_Digest *digest, char *out);

static void page_hash(AN_(MD5_CTX) *ctx, Page *page)
{
   if (!page->has_hash) {
      //VPRINT(2, "rehashing page %lu\n", page->base);
      page->has_hash = True;
      AN_(MD5_CTX) ctx2;
      AN_(MD5_Init)(&ctx2);
      UWord i;
      /* This is quite performance critical
       * It needs benchmarking before changing this code */
      UChar *d = (UChar*) page->base;
      SizeT s = 0;
      UChar *b = d;
      for (i = 0; i < PAGE_SIZE; i++) {
         if (page->va->vabits[i]) {
            if (s == 0) {
               b = d + i;
            }
            s++;
         } else if (s != 0) {
            /*int xx;
            for (xx = 0; xx < s; xx++) {
                VG_(printf)("%d,", b[xx]);
            }*/
            AN_(MD5_Update)(&ctx2, b, s);
            s = 0;
         }
      }
      if (s != 0) {
         AN_(MD5_Update)(&ctx2, b, s);
      }
      AN_(MD5_Final)(&page->hash, &ctx2);      
      char tmp[33];
      hash_to_string(&page->hash, tmp);
   }
   AN_(MD5_Update)(ctx, &page->hash, sizeof(MD5_Digest));
}

/*static void page_dump(Page *page)
{
   VG_(printf)("~~~ Page %p addr=%lu ~~~\n", page, page->base);
   int chunk_size = 0;
   UWord i;
   VA *va = page->va;
   for (i = 0; i < PAGE_SIZE; i++) {
      if (va->vabits[i]) {
         chunk_size++;
      } else {
         if (chunk_size != 0) {
            VG_(printf)("Chunk %lu-%lu %d\n",
                        page->base + i - chunk_size,
                        page->base + i,
                        chunk_size);
            chunk_size = 0;
         }
      }
   }
   if (chunk_size != 0) {
      VG_(printf)("Chunk %lu-%lu %d\n",
                  page->base + i - chunk_size,
                  page->base + i,
                  chunk_size);
   }
}*/

static void memimage_save_page_content(Page *page)
{
   UWord i;
   //UWord c = 0;

   if (page->data == NULL) {
      page->data = VG_(malloc)("an.page.data", PAGE_SIZE);
   }

   UChar *src = (UChar*) page->base;
   UChar *dst = page->data;
   VA *va = page->va;
   for (i = 0; i < PAGE_SIZE; i++) {
      if (va->vabits[i]) {
         dst[i] = src[i];
         //c++;
      }
   }
}

static void memimage_restore_page_content(Page *page)
{
   //page_dump(page);
   VPRINT(2, "memimage_restore_page_content base=%lu\n", page->base);
   UWord i;
   UChar *dst = (UChar*) page->base;
   VA *va = page->va;
   tl_assert(page->data);
   UChar *src = page->data;
   for (i = 0; i < PAGE_SIZE; i++) {
      if (va->vabits[i]) {
          dst[i] = src[i];
      }
   }
}

static void memimage_save(MemoryImage *memimage)
{
   Word size = VG_(OSetGen_Size)(current_memspace->auxmap);
   memimage->pages_count = size;
   Page **pages = (Page**) VG_(malloc)("an.memimage", size * sizeof(Page*));
   memimage->pages = pages;

   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      *pages++ = elem->page;
      if (elem->page->ref_count++ < 2) {
         memimage_save_page_content(elem->page);
      }
   }
   memimage->allocation_blocks = VG_(cloneXA)("an.memimage",
                                              current_memspace->allocation_blocks);
}

static void memimage_free(MemoryImage *memimage)
{
   UWord i;
   for (i = 0; i < memimage->pages_count; i++)
   {
      page_dispose(memimage->pages[i]);
   }
   VG_(free)(memimage->pages);
   VG_(deleteXA)(memimage->allocation_blocks);
}

static void memimage_restore(MemoryImage *memimage)
{
   OSet *old_auxmap = current_memspace->auxmap;
   OSet *auxmap = VG_(OSetGen_EmptyClone)(old_auxmap);

   UWord i;
   for (i = 0; i < memimage->pages_count; i++) {
      Page *page = memimage->pages[i];
      AuxMapEnt *nyu = (AuxMapEnt*) VG_(OSetGen_AllocNode)(auxmap, sizeof(AuxMapEnt));
      nyu->base = page->base;
      nyu->page = page;
      VG_(OSetGen_Insert)(auxmap, nyu);
      AuxMapEnt *ent = VG_(OSetGen_Lookup)(old_auxmap, nyu);
      if (ent) {
         page->ref_count++;
         if (ent->page == page) {
             continue; // We are replacing the page by the same page
         }
      }
      memimage_restore_page_content(page);
   }

   VG_(deleteXA)(current_memspace->allocation_blocks);
   current_memspace->allocation_blocks = VG_(cloneXA)("an.allocations",
                                                      memimage->allocation_blocks);

   VG_(OSetGen_ResetIter)(old_auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      page_dispose(elem->page);
   }
   VG_(OSetGen_Destroy(old_auxmap));
   current_memspace->auxmap = auxmap;
}

static void memspace_hash(AN_(MD5_CTX) *ctx)
{
   //memspace_dump();
   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      //VG_(printf)("Updating secmap %lu\n", elem->base);
      page_hash(ctx, elem->page);
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
   memimage_save(&state->memimage);

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
   memimage_restore(&state->memimage);
}


/* --------------------------------------------------------
 *  Events
 * --------------------------------------------------------*/

static VG_REGPARM(2) void trace_write(Addr addr, SizeT size)
{
   //VG_(printf)("TRACE WRITE %lu %lu\n", addr, size);
   AuxMapEnt *ent = maybe_find_in_auxmap(addr);
   make_own_copy_of_page(&ent->page);
   Page *page = ent->page;
   Addr offset = addr - page->base;
   SizeT i;
   //page_dump(page);
   for (i = 0; i < size; i++) {
      //VG_(printf)("OFFSET %lu %i\n", offset + i, page->va->vabits[offset + i]);
      if (UNLIKELY(offset + i < PAGE_SIZE && !page->va->vabits[offset + i])) {
         report_error_write(addr, size);
         tl_assert(0); // no return here
      }
   }

   // Overlap test
   Addr end = (addr & PAGE_MASK) + size;
   if (UNLIKELY(end > PAGE_SIZE)) {
      trace_write(start_of_this_page(addr) + PAGE_SIZE, end - PAGE_SIZE);
   }
}

// This function should be called when write from controller occurs ("WRITE" commands)
static void extern_write(Addr addr, SizeT size)
{
   trace_write(addr, size);
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
   VPRINT(1, "AN>> %s", str);

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
static void hash_to_string(MD5_Digest *digest, char *out)
{
   int i = 0;
   for (i = 0; i < 16; ++i) {
      unsigned char byte = digest->data[i];
      out[i*2] = hex_chars[(byte & 0xF0) >> 4];
      out[i*2+1] = hex_chars[byte & 0x0F];
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

static void process_commands_init(CommandsEnterType cet) {
   ThreadState *tst = VG_(get_ThreadState)(1);
   tl_assert(tst);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
   tl_assert(!tst->sched_jmpbuf_valid || cet == CET_REPORT);
   // Reset invalid jmpbuf to make be able generate reasonable hash of state
   // If cet == CET_REPORT then we do not return to program so we dont care about hash
   tst->arch.vex.guest_RDX = 0; // Result of client request
}

static
void process_commands(CommandsEnterType cet)
{
   process_commands_init(cet);
   char command[MAX_MESSAGE_BUFFER_LENGTH + 1];

   for (;;) {
      if (!read_command(command)) {
         VG_(exit)(1);
      }
      VPRINT(1, "AN<< %s\n", command);
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
            extern_write((Addr)addr, sizeof(int));
            *((Int*) addr) = next_token_uword();
         } else if (!VG_(strcmp(param, "buffer"))) {
            UWord *buffer = (UWord*) next_token_uword();
            UWord size = *buffer;
            extern_write((Addr)addr, size);
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
         ThreadState *tst = VG_(get_ThreadState)(1);
         tl_assert(tst);
         tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
         tl_assert(!tst->sched_jmpbuf_valid || cet == CET_REPORT);

         if (cet == CET_FINISH) { // Thread finished, so after restore, status has to be fixed
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
         MD5_Digest digest;
         char digest_str[33]; // 16 * 2 + 1
         AN_(MD5_CTX) ctx;
         AN_(MD5_Init)(&ctx);
         buffer_hash(buffer, &ctx);
         AN_(MD5_Final)(&digest, &ctx);
         hash_to_string(&digest, digest_str);
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
         MD5_Digest digest;
         char digest_str[33]; // 16 * 2 + 1
         AN_(MD5_CTX) ctx;
         AN_(MD5_Init)(&ctx);
         state_hash(&ctx);
         AN_(MD5_Final)(&digest, &ctx);
         hash_to_string(&digest, digest_str);
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

      if (!VG_(strcmp)(cmd, "STATS")) {
          VG_(snprintf)(command,
                        MAX_MESSAGE_BUFFER_LENGTH,
                        "pages %ld|"
                        "active-pages %ld\n",
                        stats.pages,
                        VG_(OSetGen_Size)(current_memspace->auxmap));
          write_message(command);
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
   VPRINT(2, "new_mem_mmap %lu-%lu %lu %d %d %d\n", a, a + len, len, rr, ww, xx);

   if (rr && ww) {      
      make_mem_defined(a, len);
   } else {
      make_mem_noaccess(a, len);
   }

   //memspace_dump();
}

static
void new_mem_mprotect ( Addr a, SizeT len, Bool rr, Bool ww, Bool xx )
{
   VPRINT(2, "new_mem_mprotect %lu-%lu %lu %d %d %d\n", a, a + len, len, rr, ww, xx);

   if (rr && ww) {
      make_mem_defined(a, len);
   } else {
      make_mem_noaccess(a, len);
   }
}

static
void mem_unmap(Addr a, SizeT len)
{
   VPRINT(2, "unmap %lu-%lu %lu\n", a, a + len, len);
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
   VPRINT(2, "new_mem_startup %lu-%lu %lu\n", a, a + len, len);
   new_mem_mmap(a, len, rr, ww, xx, di_handle);
}

static void new_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("NEW STACK %lx %lu\n", a - VG_STACK_REDZONE_SZB, len);
   make_mem_undefined(a - VG_STACK_REDZONE_SZB, len);
}

static
void new_mem_stack_signal(Addr a, SizeT len, ThreadId tid)
{
   //VG_(printf)("STACK SIGNAL %lx %lu", a - VG_STACK_REDZONE_SZB, len);
   make_mem_undefined(a - VG_STACK_REDZONE_SZB, len);
}

static void die_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("DIE STACK %lx %lu\n", a - VG_STACK_REDZONE_SZB, len);
   make_mem_noaccess(a - VG_STACK_REDZONE_SZB, len);
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

   states_table = VG_(HT_construct)("an.states");
   memspace_init();

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
void event_write(IRSB *sb, IRExpr *addr, Int dsize)
{
   IRExpr **args = mkIRExprVec_2(addr, mkIRExpr_HWord(dsize));
   IRDirty *di   = unsafeIRDirty_0_N( /*regparms*/2, 
                             "trace_write", VG_(fnptr_to_fnentry)(trace_write),
                             args);
   addStmtToIRSB( sb, IRStmt_Dirty(di) );
}

static
IRSB* an_instrument ( VgCallbackClosure* closure,
                      IRSB* sb_in,
                      VexGuestLayout* layout,
                      VexGuestExtents* vge,
                      VexArchInfo* archinfo_host,
                      IRType gWordTy, IRType hWordTy )
{
   Int i;
   IRSB *sb_out;
   IRTypeEnv* tyenv = sb_in->tyenv;

   if (gWordTy != hWordTy) {
      /* We don't currently support this case. */
      VG_(tool_panic)("host/guest word size mismatch");
   }

   sb_out = deepCopyIRSBExceptStmts(sb_in);

   i = 0;
   while (i < sb_in->stmts_used && sb_in->stmts[i]->tag != Ist_IMark) {
      addStmtToIRSB( sb_out, sb_in->stmts[i] );
      i++;
   }

   for (/*use current i*/; i < sb_in->stmts_used; i++) {
      IRStmt* st = sb_in->stmts[i];
      switch (st->tag) {

         case Ist_Store: {
            IRExpr* data = st->Ist.Store.data;
            IRType  type = typeOfIRExpr(tyenv, data);
            tl_assert(type != Ity_INVALID);
            event_write(sb_out, st->Ist.Store.addr, sizeofIRType(type) );
            addStmtToIRSB(sb_out, st);
            break;
         }
         default:
            addStmtToIRSB(sb_out, st);
            break;
      }
   }

   return sb_out;
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

static void* client_malloc (ThreadId tid, SizeT n)
{   
   //memspace_dump();
    Addr addr = memspace_alloc(n);
    make_mem_undefined(addr, n);
    VPRINT(2, "client_malloc address=%lu size=%lu\n", addr, n);
    return (void*) addr;
}

static
void* user_memalign (ThreadId tid, SizeT alignB, SizeT n)
{
    VG_(tool_panic)("user_memalign: Not implemented");
}

static
void* user_calloc (ThreadId tid, SizeT nmemb, SizeT size1)
{
   VG_(tool_panic)("user_calloc: Not implemented");
}

static
void* user_realloc(ThreadId tid, void* p_old, SizeT new_szB)
{
    VG_(tool_panic)("user_realloc: Not implemented");
}

static
SizeT client_malloc_usable_size(ThreadId tid, void* p)
{
    VG_(tool_panic)("client_malloc_usable_size: Not implemented");
}


static void client_free (ThreadId tid, void *a)
{
    VPRINT(2, "client_free %lu\n", (Addr) a);
    SizeT size = memspace_free((Addr) a);
    make_mem_noaccess((Addr) a, size);
}

/*static
void check_mem_is_defined ( CorePart part, ThreadId tid, const HChar* s,
                            Addr base, SizeT size )
{
    VG_(tool_panic)("check_mem_is_defined: Not implemented");
}

static
void check_mem_is_defined_asciiz ( CorePart part, ThreadId tid,
                                   const HChar* s, Addr str )
{
    VG_(tool_panic)("check_mem_is_defined_asciiz: Not implemented");
}

static
void check_mem_is_addressable ( CorePart part, ThreadId tid, const HChar* s,
                                Addr base, SizeT size )
{
    VG_(tool_panic)("check_mem_is_addressable: Not implemented");
}*/

static
void post_mem_write(CorePart part, ThreadId tid, Addr a, SizeT len)
{
   make_mem_defined(a, len);
}

static void post_reg_write ( CorePart part, ThreadId tid,
                                PtrdiffT offset, SizeT size)
{
   //VG_(tool_panic)("post_reg_write: Not implemented");
}

static
void post_reg_write_clientcall ( ThreadId tid,
                                    PtrdiffT offset, SizeT size, Addr f)
{
   post_reg_write(/*dummy*/0, tid, offset, size);
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

   VG_(needs_malloc_replacement)  (client_malloc,
                                   client_malloc, //MC_(__builtin_new),
                                   client_malloc, //MC_(__builtin_vec_new),
                                   user_memalign, //MC_(memalign),
                                   user_calloc, //MC_(calloc),
                                   client_free, //MC_(free),
                                   client_free, //MC_(__builtin_delete),
                                   client_free, //MC_(__builtin_vec_delete),
                                   user_realloc, //MC_(realloc),
                                   client_malloc_usable_size, //MC_(malloc_usable_size),
                                   0);

   VG_(track_new_mem_mmap)    (new_mem_mmap);
   VG_(track_new_mem_startup) (new_mem_startup);
   VG_(track_change_mem_mprotect) (new_mem_mprotect);

   VG_(track_copy_mem_remap)      (copy_address_range_state);
   VG_(track_die_mem_stack_signal)(mem_unmap);
   VG_(track_die_mem_brk)         (mem_unmap);
   VG_(track_die_mem_munmap)      (mem_unmap);

   /*VG_(track_new_mem_mmap)    (an_new_mem_mmap);
   VG_(track_new_mem_brk)     (an_new_mem_brk);
   VG_(needs_client_requests) (an_handle_client_request);*/

   /*VG_(needs_restore_thread)(an_restore_thread);*/
   VG_(track_new_mem_stack_signal) (new_mem_stack_signal);
   VG_(track_new_mem_stack) (new_mem_stack);
   VG_(track_die_mem_stack) (die_mem_stack);

   VG_(track_ban_mem_stack)       (make_mem_noaccess);

   /*VG_(track_pre_mem_read)        (check_mem_is_defined );
   VG_(track_pre_mem_read_asciiz) (check_mem_is_defined_asciiz);
   VG_(track_pre_mem_write)       (check_mem_is_addressable);*/
   VG_(track_post_mem_write)      (post_mem_write);
   VG_(track_post_reg_write)                  (post_reg_write);
   VG_(track_post_reg_write_clientcall_return)(post_reg_write_clientcall);

   VG_(needs_client_requests) (an_handle_client_request);
}

VG_DETERMINE_INTERFACE_VERSION(an_pre_clo_init)

/*--------------------------------------------------------------------*/
/*--- end                                                          ---*/
/*--------------------------------------------------------------------*/
