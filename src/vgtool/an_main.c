
/*--------------------------------------------------------------------*/
/*--- Aislinn                                                      ---*/
/*--------------------------------------------------------------------*/

/*
   This file is part of Aislinn

   Copyright (C) 2014, 2015 Stanislav Bohm

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
#include "pub_tool_transtab.h"
#include "pub_tool_machine.h"     // VG_(fnptr_to_fnentry)
#include "pub_tool_vki.h"
#include "../../include/aislinn.h"
#include "md5/md5.h"

#include <linux/unistd.h>

/* Here, the internals of valgring are exponsed
 * But aislinn cannot work without it.
 * Some sufficient public interface should be
 * made in the future */
#include "../coregrind/pub_core_threadstate.h"
#include "../coregrind/pub_core_libcfile.h"
#include "../coregrind/pub_core_syscall.h"
#include "../coregrind/pub_core_aspacemgr.h"
#include "../coregrind/pub_core_mallocfree.h"
#include "../coregrind/pub_core_clientstate.h"
extern SysRes ML_(am_do_munmap_NO_NOTIFY)(Addr start, SizeT length);

#define INLINE    inline __attribute__((always_inline))
#define NOINLINE __attribute__ ((noinline))

#define VPRINT(level, ...) if (verbosity_level >= (level)) { VG_(printf)(__VA_ARGS__); }

#define PAGE_SIZE 65536
#define PAGE_MASK (PAGE_SIZE-1)                        /* DO NOT CHANGE */
#define REAL_PAGES_IN_PAGE (PAGE_SIZE / VKI_PAGE_SIZE) /* DO NOT CHANGE */

//#define VA_CHUNKS 16384
#define VA_CHUNKS 65536
#define PAGE_OFF(a) ((a) & PAGE_MASK)

#define MEM_NOACCESS  0 // 00
#define MEM_UNDEFINED 1 // 01
#define MEM_READONLY  2 // 10
#define MEM_DEFINED   3 // 11

#define MEM_READ_MASK  2 // 10
#define MEM_WRITE_MASK 1 // 01

#define PAGEFLAG_UNMAPPED 0 // 0000
#define PAGEFLAG_MAPPED   1 // 0001
#define PAGEFLAG_READ     2 // 0100
#define PAGEFLAG_WRITE    4 // 0010
#define PAGEFLAG_EXECUTE  8 // 1000

#define PAGEFLAG_RW (PAGEFLAG_MAPPED | PAGEFLAG_READ | PAGEFLAG_WRITE)

typedef
   struct {
      Int ref_count;
      UChar vabits[VA_CHUNKS];
   } VA;

typedef
   enum {
      INVALID_HASH,
      VALID_HASH,
      EMPTY,
   } PageStatus;

typedef
   struct {
      Addr base;
      Int ref_count;
      UChar page_flags[REAL_PAGES_IN_PAGE];
      VA *va;
      UChar *data;
      PageStatus status;
      MD5_Digest hash;
   } Page;

// Must be nonconflicting with bits in PAGEFLAG
#define TRANSPORT_PAGEFLAG_MASK      0xF0 // 11110000
#define TRANSPORT_PAGEFLAG_NOACCESS  0x00 // 00000000
#define TRANSPORT_PAGEFLAG_UNDEFINED 0x10 // 00010000
#define TRANSPORT_PAGEFLAG_FULL      0x20 // 00100000
#define TRANSPORT_PAGEFLAG_DEFINED   0x30 // 00110000
#define TRANSPORT_PAGEFLAG_READONLY  0x40 // 01000000
#define TRANSPORT_PAGEFLAG_VAONLY    0x50 // 01010000

typedef
   struct {
      Addr base;
      //MD5_Digest hash;
      UChar flags[REAL_PAGES_IN_PAGE];
   } TransportPageHeader;

typedef
   struct {
      Addr    base;
      Page* page;
   } AuxMapEnt;

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
      SizeT requested_size;
   } AllocationBlock;

#define MEMSPACE_PAGE_CACHE_SIZE 12

typedef
   struct {
      Int page_cache_size;
      Page *page_cache[MEMSPACE_PAGE_CACHE_SIZE];
      OSet *auxmap;
      Addr heap_space;
      Addr heap_space_end;
      XArray *allocation_blocks;
      Vg_AislinnCallAnswer *answer;
   } MemorySpace;

typedef
   struct {
      Page **pages;
      UWord pages_count;
      XArray *allocation_blocks;
      Vg_AislinnCallAnswer *answer;
   } MemoryImage;

typedef
   // First two entries has to correspond to VgHashNode
   struct {
      struct State *next;
      UWord id;
      MemoryImage memimage;
      ThreadState threadstate;
   } State;

typedef
   struct {
      UWord pages_count;
      Word allocation_blocks_count;
      Vg_AislinnCallAnswer *answer;
      ThreadState threadstate;
   } TransportStateHeader;

typedef
  // First two entries has to correspond to VgHashNode
  struct {
     struct Buffer *next;
     UWord id;
     SizeT size;
     // data follows ...
  } Buffer;

/* Maximal stack size, this is default on amd64,
   But the correct way is to read the actual value from Valgrind
   (somewhere from structures from m_stacks.c)
 */
#define STACK_SIZE (8 * 1024 * 1024)

/* Global variables */

static int verbosity_level = 0;
static SizeT heap_max_size = 512 * 1024 * 1024; // Default: 512M
static SizeT redzone_size = 16;

static MemorySpace *current_memspace = NULL;
static VgHashTable *state_table;
static VgHashTable *buffer_table;

static Int control_socket = -1;

static struct {
    Bool enable;
    UWord count_instructions;
    UWord count_allocations;
    UWord size_allocations;
} profile;

#define MAX_MESSAGE_BUFFER_LENGTH 20000
static char message_buffer[MAX_MESSAGE_BUFFER_LENGTH];
static Int message_buffer_size = 0;

static Int server_port = -1;
static Int identification = 0; // For debugging purpose when verbose > 0

static VA *uniform_va[4];

static struct {
   // What syscall is monitored
   Bool syscall_write;
   Bool syscall_read;
   Bool syscall_open;
   Bool syscall_close;

   // Result from callback
   Bool drop_current_syscall;
   UWord return_value; // Valid if drop_current_syscall is True
} capture_syscalls;

static struct {
   Word pages; // Number of currently allocated pages
   Word vas; // Number of VAs
   Word buffers_size; // Sum of buffer sizes
} stats;

typedef
   enum {
      CET_FINISH,
      CET_CALL,
      CET_FUNCTION,
      CET_SYSCALL,
      CET_REPORT,      
   } CommandsEnterType;

static void write_message(const char *str);
static void process_commands(CommandsEnterType cet, Vg_AislinnCallAnswer *answer);
static void* client_malloc (ThreadId tid, SizeT n);
static void client_free (ThreadId tid, void *a);

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

/* --------------------------------------------------------
 *  Reports
 * --------------------------------------------------------*/

static NOINLINE void report_error(const char *code)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH, "REPORT %s\n", code);
   write_message(message);
   process_commands(CET_REPORT, NULL);
   tl_assert(0); // no return from process_commands
}

static NOINLINE void report_error_write(Addr addr, SizeT size)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                     "invalidwrite 0x%lx %lu", addr, size);
   report_error(message);
}

static NOINLINE void report_error_read(Addr addr, SizeT size)
{
   char message[MAX_MESSAGE_BUFFER_LENGTH];
   VG_(snprintf)(message, MAX_MESSAGE_BUFFER_LENGTH,
                 "invalidread 0x%lx %lu", addr, size);
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
   Addr heap_space = (Addr) VG_(arena_memalign)
           (VG_AR_CORE, "an.heap", PAGE_SIZE, heap_max_size);
   tl_assert(heap_space % PAGE_SIZE == 0); // Heap is propertly aligned


   tl_assert(heap_space != 0);
   VPRINT(2, "memspace_init: heap %lx-%lx\n", heap_space, heap_space + heap_max_size);

   MemorySpace *ms = VG_(malloc)("an.memspace", sizeof(MemorySpace));
   VG_(memset)(ms, 0, sizeof(MemorySpace));
   ms->auxmap = VG_(OSetGen_Create)(/*keyOff*/  offsetof(AuxMapEnt,base),
                                    /*fastCmp*/ NULL,
                                    VG_(malloc), "an.auxmap", VG_(free));
   ms->heap_space = heap_space;
   ms->heap_space_end = heap_space + heap_max_size;
   ms->allocation_blocks = VG_(newXA)
      (VG_(malloc), "an.allocations", VG_(free), sizeof(AllocationBlock));
   AllocationBlock block;
   block.address = heap_space;
   block.type = BLOCK_END;
   VG_(addToXA)(ms->allocation_blocks, &block);

   tl_assert(current_memspace == NULL);
   current_memspace = ms;
}

/*static void mem_dump(void *addr, SizeT size)
{
    SizeT i;
    UChar *d = addr;
    VG_(printf)("Mem(0x%lx, %lu):", (Addr) addr, size);
    for (i = 0; i < size; i++) {
        VG_(printf)("%02x", (int) d[i]);
    }
    VG_(printf)("\n");
}*/

static void hash_to_string(MD5_Digest *digest, char *out);

static void page_dump(Page *page)
{
   char tmp[REAL_PAGES_IN_PAGE + 1];
   const char *name = "";

   if (page->base >= current_memspace->heap_space && page->base < current_memspace->heap_space_end) {
        name = "heap";
   } else {
       Addr end = VG_(clstk_end);
       Addr start = end - STACK_SIZE;
       if (page->base >= start_of_this_page(start) &&
           page->base <= start_of_this_page(end))
       {
           name = "stack";
       }
   }


   UWord i;

   for (i = 0; i < REAL_PAGES_IN_PAGE; i+=1) {
         if (page->page_flags[i] == PAGEFLAG_UNMAPPED) {
              tmp[i] = '!'; // Unmapped
         } else if (page->page_flags[i] & PAGEFLAG_RW) {
             tmp[i] = '*'; // RW
         } else if (page->page_flags[i] & PAGEFLAG_READ) {
             tmp[i] = 'R'; // Readonly
         } else if (page->page_flags[i] & PAGEFLAG_WRITE) {
             tmp[i] = 'W'; // write only
         } else if (page->page_flags[i] & PAGEFLAG_MAPPED) {
             tmp[i] = '-'; // No access
         } else {
             tmp[i] = '?'; // All other cases
         }
   }
   tmp[REAL_PAGES_IN_PAGE] = 0;

   char hashstr[32];
   if (page->status == VALID_HASH) {
        hash_to_string(&page->hash, hashstr);
   } else if (page->status == EMPTY) {
        VG_(strcpy)(hashstr, "<empty>");
   } else {
       VG_(strcpy)(hashstr, "<invalid>");
   }

   const char *vastr = "";

   if (page->va == uniform_va[MEM_DEFINED]) {
       vastr = " (DEF)";
   }

   if (page->va == uniform_va[MEM_UNDEFINED]) {
       vastr = " (UNDEF)";
   }

   if (page->va == uniform_va[MEM_NOACCESS]) {
       vastr = " (NOA)";
   }

   if (page->va == uniform_va[MEM_READONLY]) {
       vastr = " (RDONLY)";
   }

   VG_(printf)("~~~ Page %p base=0x%lx data=%p va=%p%s hash=%s %s %s ~~~\n", page, page->base, page->data, page->va, vastr, hashstr, name, tmp);



   VA *va = page->va;

   if (va == NULL) {
       VG_(printf("VA == NULL\n"));
       return;
   }

   char prev = va->vabits[0];
   int chunk_size = 1;

   for (i = 1; i < PAGE_SIZE; i++) {
      if (va->vabits[i] == prev) {
         chunk_size++;
      } else {
         if (chunk_size != 0) {
            if (prev != 0) {
                VG_(printf)("Chunk 0x%lx-0x%lx %d perm=%d\n",
                            page->base + i - chunk_size,
                            page->base + i,
                            chunk_size,
                            prev);
                //UWord j;
                //UChar *data = page->data;
                //if (data == NULL) {
                //    data = (UChar*) page->base;
                //}
                //for (j = i - chunk_size; j < i; j++) {
                //    VG_(printf)("%02x", (int) data[j]);
                //}
                //VG_(printf)("\n");
            }
            prev = va->vabits[i];
            chunk_size = 1;
         }
      }
   }
   if (chunk_size != 0 && prev && prev != 0xFF) {
      VG_(printf)("Chunk 0x%lx-0x%lx %d perm=%d\n",
                  page->base + i - chunk_size,
                  page->base + i,
                  chunk_size,
                  prev);
   }
}

/*
static
void memspace_dump(void)
{
   VG_(printf)("========== MEMSPACE DUMP ===========\n");
   VG_(OSetGen_ResetIter)(current_memspace->auxmap);
   AuxMapEnt *elem;
   while ((elem = VG_(OSetGen_Next(current_memspace->auxmap)))) {
      VG_(printf)("Auxmap 0x%lx-0x%lx refs=%d data=%lu\n",
                  elem->base,
                  elem->base + PAGE_SIZE,
                  elem->page->ref_count,
                  (Addr) elem->page->data);
      page_dump(elem->page);
   }

   XArray *a = current_memspace->allocation_blocks;
   Word i;
   for (i = 0; i < VG_(sizeXA)(a); i++) {
       AllocationBlock *block = VG_(indexXA)(a, i);
       VG_(printf)("%lu: addr=0x%lx type=%d\n", i, block->address, block->type);
   }
}
*/

/*
static void memspace_sanity_check(void)
{
   memspace_dump();
   XArray *a = current_memspace->allocation_blocks;
   Word i;
   SizeT size = VG_(sizeXA)(a);
   tl_assert(size > 0);

   AllocationBlock *block, *next;+   for (i = 0; i < size - 1; i++) {
       block = VG_(indexXA)(a, i);
       next = VG_(indexXA)(a, i + 1);
       tl_assert(next->address % 4 == 0);
       tl_assert(next->address > block->address);
       tl_assert(block->type == BLOCK_USED || block->type == BLOCK_FREE);
       tl_assert(block->type != BLOCK_FREE || !next->type == BLOCK_FREE);
   }
   block = VG_(indexXA)(a, size - 1);
   tl_assert(block->type == BLOCK_END);
}
*/

static
Addr memspace_alloc(SizeT alloc_size, SizeT allign)
{
   profile.count_allocations += 1;
   profile.size_allocations += alloc_size;

   SizeT requested_size = alloc_size;
   alloc_size += redzone_size;
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
            Addr old_address = block->address;
            Addr address = ((old_address - 1) / allign + 1) * allign;
            SizeT padding = address - block->address;
            if (s >= alloc_size + padding) {
                block->type = BLOCK_USED;
                block->requested_size = requested_size;
                if (padding > 0) {
                    block->address = address;
                    AllocationBlock new_block;
                    new_block.type = BLOCK_FREE;
                    new_block.address = old_address;
                    VG_(insertIndexXA)(a, i, &new_block);
                    i++;
                }
                SizeT diff = s - (alloc_size + padding);
                if (diff > 0) {
                    AllocationBlock new_block;
                    new_block.type = BLOCK_FREE;
                    new_block.address = address + alloc_size;
                    VG_(insertIndexXA)(a, i + 1, &new_block);
                }
                return address;
            }
         }
      }
      block = next;
      i++;
   }

   // No sufficient block found, create a new one
   Addr old_address = block->address;
   Addr address = ((old_address - 1) / allign + 1) * allign;
   SizeT padding = address - block->address;

   if (padding > 0) {
       block->type = BLOCK_FREE;
       AllocationBlock new_block;
       new_block.type = BLOCK_USED;
       new_block.address = address;
       new_block.requested_size = requested_size;
       VG_(addToXA)(a, &new_block);
   } else {
       block->type = BLOCK_USED;
       block->requested_size = requested_size;
   }

   AllocationBlock new_block;
   new_block.type = BLOCK_END;
   new_block.requested_size = requested_size;
   new_block.address = address + alloc_size;

   if (UNLIKELY(new_block.address - \
                current_memspace->heap_space >= heap_max_size)) {
      report_error("heaperror");
      tl_assert(0);
   }

   VG_(addToXA)(a, &new_block);
   return address;
}

static SizeT memspace_block_size(Addr address)
{
    XArray *a = current_memspace->allocation_blocks;
    Word i, s = VG_(sizeXA)(a);
    AllocationBlock *block = NULL, *next;
    for (i = 0; i < s; i++) {
        block = VG_(indexXA)(a, i);
        if (block->address == address) {
            break;
        }
    }
    tl_assert(block && block->type == BLOCK_USED);
    next = VG_(indexXA)(a, i + 1);
    SizeT size = next->address - address;
    return size;
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

static void memspace_add_to_page_cache(Page *page)
{
   MemorySpace *ms = current_memspace;
   if (ms->page_cache_size < MEMSPACE_PAGE_CACHE_SIZE) {
      ms->page_cache[ms->page_cache_size] = page;
      ms->page_cache_size++;
      return;
   }
   for (Int i = MEMSPACE_PAGE_CACHE_SIZE - 1; i > 0; i--) {
      ms->page_cache[i] = ms->page_cache[i - 1];
   }
   ms->page_cache[0] = page;
}

static INLINE AuxMapEnt* find_page_in_auxmap (Addr base)
{
   AuxMapEnt  key;
   AuxMapEnt* res;
   key.base = base;
   res = VG_(OSetGen_Lookup)(current_memspace->auxmap, &key);
   return res;
}

static INLINE AuxMapEnt *find_addr_in_auxmap(Addr a)
{
   a &= ~(Addr) PAGE_MASK;
   return find_page_in_auxmap(a);
}

static VA *va_new(void)
{
   stats.vas++;
   VA *va = VG_(malloc)("an.va", sizeof(VA));
   va->ref_count = 1;
   return va;
}

static VA *va_clone(VA *va)
{
   VA *new_va = va_new();
   VG_(memcpy)(new_va->vabits, va->vabits, sizeof(va->vabits));
   return new_va;
}

static void va_dispose(VA *va)
{
   va->ref_count--;
   if (va->ref_count <= 0) {
      tl_assert(va->ref_count == 0);
      VG_(free)(va);
      stats.vas--;
   }
}

static Page *page_new(Addr a)
{
    stats.pages++;

    Page *page = (Page*) VG_(malloc)("an.page", sizeof(Page));
    page->base = a;
    page->ref_count = 1;
    page->status = EMPTY;
    page->data = NULL;
    page->va = NULL;
    VPRINT(3, "page_new %p base=%lx\n", page, a);
    return page;
}

static Page *page_new_empty(Addr a)
{
   Page *page = page_new(a);
   page->va = uniform_va[MEM_NOACCESS];
   page->va->ref_count++;
   if (a >= current_memspace->heap_space && a < current_memspace->heap_space_end) {
       VG_(memset)(page->page_flags, PAGEFLAG_RW, sizeof(page->page_flags));
   } else {
       VG_(memset)(page->page_flags, PAGEFLAG_UNMAPPED, sizeof(page->page_flags));

       Addr end = VG_(clstk_end);
       Addr start = end + 1 - STACK_SIZE;
       if (a >= start_of_this_page(start) &&
           a <= start_of_this_page(end))
       {
            tl_assert(start % VKI_PAGE_SIZE == 0);
            Int i;
            for (i = 0; i < REAL_PAGES_IN_PAGE; i++, a += VKI_PAGE_SIZE) {
                if (a >= start && a <= end) {
                    page->page_flags[i] = PAGEFLAG_RW;
                }
            }
       }
   }

   return page;
}

// Page is cloned without data and hash
static Page* page_clone(Page *page)
{
   Page *new_page = page_new(page->base);
   new_page->status = page->status;
   page->va->ref_count++;
   new_page->va = page->va;
   VG_(memcpy)(new_page->page_flags, page->page_flags, sizeof(page->page_flags));
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
      va_dispose(page->va);
      VG_(free)(page);
   }
}

static AuxMapEnt* find_or_alloc_ent_in_auxmap(Addr a)
{
   AuxMapEnt *nyu, *res;

   a &= ~(Addr) PAGE_MASK;
   res = find_page_in_auxmap(a);
   if (LIKELY(res))
      return res;

   nyu = (AuxMapEnt*) VG_(OSetGen_AllocNode)(
      current_memspace->auxmap, sizeof(AuxMapEnt));
   nyu->base = a;
   nyu->page = NULL;
   VG_(OSetGen_Insert)(current_memspace->auxmap, nyu);
   return nyu;
}

static void INLINE page_update(Page *page)
{
   Addr base = page->base;
   MemorySpace *ms = current_memspace;
   for (UInt i = 0; i < ms->page_cache_size; i++) {
      if (ms->page_cache[i]->base == base) {
         ms->page_cache[i] = page;
         break;
      }
   }
   AuxMapEnt *res = find_or_alloc_ent_in_auxmap(base);
   res->page = page;
}

static INLINE Page* page_prepare_for_write_data(Page *page) {
   VPRINT(3, "page_prepare_for_write_data base=%lx refcount=%d page=%p\n",
          page->base, page->ref_count, page);
   if (UNLIKELY(page->ref_count >= 2)) {
      page->ref_count--;
      Page *new_page = page_clone(page);
      new_page->status = INVALID_HASH;
      page_update(new_page);
      return new_page;
   }

   page->status = INVALID_HASH;
   return page;
}

static INLINE void page_set_va(Page *page, VA *va) {
   page = page_prepare_for_write_data(page);
   va_dispose(page->va);
   page->va = va;
   va->ref_count++;
}

static INLINE void page_set_va_no_ref_inc(Page *page, VA *va) {
   page = page_prepare_for_write_data(page);
   va_dispose(page->va);
   page->va = va;
}

static INLINE Page* page_prepare_for_write_va(Page *page) {
   VPRINT(3, "page_prepare_for_write_va base=%lx refcount=%d page=%p\n",
          page->base, page->ref_count, page);
   if (UNLIKELY(page->ref_count >= 2)) {
      page->ref_count--;
      Page *new_page = page_clone(page);
      page->va->ref_count--;
      new_page->va = va_clone(page->va);
      new_page->status = INVALID_HASH;
      page_update(new_page);
      return new_page;
   }

   if (UNLIKELY(page->va->ref_count >= 2)) {
      page->va->ref_count--;
      page->va = va_clone(page->va);
      page->status = INVALID_HASH;
      return page;
   }
   page->status = INVALID_HASH;
   return page;
}


// same as get_page_ptr, but do not create one if it cannot be found
static INLINE Page* get_page_or_null(Addr a)
{
    a &= ~(Addr) PAGE_MASK;

    MemorySpace *ms = current_memspace;
    if (ms->page_cache_size && ms->page_cache[0]->base == a) {
       return ms->page_cache[0];
    }
    for (Int i = 1; i < ms->page_cache_size; i++) {
       if (ms->page_cache[i]->base == a) {
          Page *page = ms->page_cache[i];
          while(i > 0) {
             ms->page_cache[i] = ms->page_cache[i-1];
             i--;
          }
          ms->page_cache[0] = page;
          return page;
       }
    }

    //VG_(printf)("CACHE MISS %lx %d\n", a, ms->page_cache_size);

    AuxMapEnt *res = find_page_in_auxmap(a);
    if (UNLIKELY(!res)) {
        return NULL;
    }
    Page *page = res->page;
    memspace_add_to_page_cache(page);
    return page;
}

static INLINE Page* get_page(Addr a)
{
   a &= ~(Addr) PAGE_MASK;
   MemorySpace *ms = current_memspace;
   if (ms->page_cache_size && ms->page_cache[0]->base == a) {
      return ms->page_cache[0];
   }
   for (Int i = 1; i < ms->page_cache_size; i++) {
      if (ms->page_cache[i]->base == a) {
         Page *page = ms->page_cache[i];
         while(i > 0) {
            ms->page_cache[i] = ms->page_cache[i-1];
            i--;
         }
         ms->page_cache[0] = page;
         return page;
      }
   }

   //VG_(printf)("CACHE MISS %lx %d\n", a, ms->page_cache_size);

   AuxMapEnt *res = find_page_in_auxmap(a);
   if (UNLIKELY(!res)) {
      res = (AuxMapEnt*) VG_(OSetGen_AllocNode)(
         current_memspace->auxmap, sizeof(AuxMapEnt));
      res->base = a;
      res->page = page_new_empty(a);
      VG_(OSetGen_Insert)(current_memspace->auxmap, res);
      return res->page;
   }
   Page *page = res->page;
   memspace_add_to_page_cache(page);
   return page;
}



static
Bool check_address_range_perms (
                Addr a, SizeT lenT, UChar perm_mask, Addr *first_invalid_mem)
{
   VA* va;
   Page *page;
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

   page = get_page_or_null(a);
   if (!page) {
       if (first_invalid_mem) {
            *first_invalid_mem = a;
       }
       return False;
   }
   va = page->va;
   pg_off = PAGE_OFF(a);
   while (lenA > 0) {
      if (UNLIKELY(!(va->vabits[pg_off] & perm_mask))) {
          if (first_invalid_mem) {
            *first_invalid_mem = start_of_this_page(a) + pg_off;
          }
          return False;
      }
      pg_off++;
      lenA--;
   }

   a = start_of_this_page (a) + PAGE_SIZE;

part2:
   while (lenB >= PAGE_SIZE) {
      page = get_page_or_null(a);
      if (!page) {
          if (first_invalid_mem) {
               *first_invalid_mem = a;
          }
          return False;
      }
      va = page->va;

      for (pg_off = 0; pg_off < PAGE_SIZE; pg_off++) {
         if (UNLIKELY(!(va->vabits[pg_off] & perm_mask))) {
             if (first_invalid_mem) {
               *first_invalid_mem = start_of_this_page(a) + pg_off;
             }
             return False;
         }
      }
      lenB -= PAGE_SIZE;
      a += PAGE_SIZE;
   }

   if (lenB == 0) {
      return True;
   }

   tl_assert(lenB < PAGE_SIZE);

   page = get_page_or_null(a);
   if (!page) {
       if (first_invalid_mem) {
            *first_invalid_mem = a;
       }
       return False;
   }
   va = page->va;
   pg_off = 0;
   while (lenB > 0) {
      if (UNLIKELY((!(va->vabits[pg_off] & perm_mask)))) {
          if (first_invalid_mem) {
            *first_invalid_mem = start_of_this_page(a) + pg_off;
          }
          return False;
      }
      pg_off++;
      lenB--;
   }
   return True;
}

static void fill_undefined_memory(Addr addr, SizeT size)
{
    if (size == 0) {
        return;
    }

    Page *page = get_page(addr);
    for(;;) {
        Addr offset = PAGE_OFF(addr);
        if (page->va->vabits[offset] == MEM_UNDEFINED) {
            HChar *a = (HChar*) addr;
            *a = 0;
        }

        size--;
        if (size == 0) {
            return;
        }

        addr++;
        if (is_start_of_page(addr)) {
            page = get_page(addr);
        }
    }
}


static INLINE Bool check_is_writable(Addr addr, SizeT size, Addr *first_invalid_addr)
{
    //memspace_dump();
    return check_address_range_perms(addr, size, MEM_WRITE_MASK, first_invalid_addr);
}

static INLINE Bool check_is_readable(Addr addr, SizeT size, Addr *first_invalid_addr)
{
    return check_address_range_perms(addr, size, MEM_DEFINED, first_invalid_addr);
}

static
void set_address_range_page_flags(Addr a, SizeT lenT, UChar value)
{
   tl_assert(a % VKI_PAGE_SIZE == 0);
   if (lenT == 0) {
      return;
   }

   for(;;) {
      Page *page = get_page(a);
      tl_assert(page->ref_count == 1);
      UWord pg_off = PAGE_OFF(a);

      /*
      // Dirty hack, to make sure that MEM_DEFINED or MEM_READONLY has not unmapped page
      VA *va = page->va;
      if (value != PAGEFLAG_RW && (va == uniform_va[MEM_DEFINED] || va == uniform_va[MEM_READONLY])) {
         page_set_va_no_ref_inc(&page, va_clone(page->va));
      }*/

      UInt i;
      for (i = pg_off / VKI_PAGE_SIZE; i < REAL_PAGES_IN_PAGE; i++) {
         page->page_flags[i] = value;
         if (lenT <= VKI_PAGE_SIZE) {
            //page_dump(page);
            return;
         }
         lenT -= VKI_PAGE_SIZE;
      }
      a = start_of_this_page(a);
      a += PAGE_SIZE;
   }
}

static
void set_address_range_perms (
                Addr a, SizeT lenT, UChar perm)
{
   VA* va;
   Page *page;
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
   page = get_page(a);
   page = page_prepare_for_write_va(page);
   va = page->va;
   pg_off = PAGE_OFF(a);

   while (lenA > 0) {
      va->vabits[pg_off] = perm;
      pg_off++;
      lenA--;
   }

   /*len = lenA / VKI_PAGE_SIZE;
   UInt i = PAGE_OFF(a) / PAGE_SIZE;

   while (len >)*/

   a = start_of_this_page (a) + PAGE_SIZE;

part2:
   while (lenB >= PAGE_SIZE) {
      page = get_page(a);
      page_set_va(page, uniform_va[perm]);
      lenB -= PAGE_SIZE;
      a += PAGE_SIZE;
   }

   if (lenB == 0) {
       return;
   }

   tl_assert(lenB < PAGE_SIZE);
   page = get_page(a);
   page = page_prepare_for_write_va(page);
   va = page->va;
   pg_off = 0;
   while (lenB > 0) {
      va->vabits[pg_off] = perm;
      pg_off++;
      lenB--;
   }
}

static INLINE void make_mem_undefined(Addr a, SizeT len)
{
   set_address_range_perms(a, len, MEM_UNDEFINED);
}

static INLINE void make_mem_defined(Addr a, SizeT len)
{
   set_address_range_perms(a, len, MEM_DEFINED);
}

static INLINE void make_mem_readonly(Addr a, SizeT len)
{
   set_address_range_perms(a, len, MEM_READONLY);
}

static INLINE void make_mem_noaccess(Addr a, SizeT len)
{
   set_address_range_perms(a, len, MEM_NOACCESS);
}

static void page_hash(AN_(MD5_CTX) *ctx, Page *page)
{
   if (page->status == INVALID_HASH) {
      if (page->va == uniform_va[MEM_NOACCESS] || page->va == uniform_va[MEM_UNDEFINED]) {
         page->status = EMPTY;
         return;
      }
      //VPRINT(2, "rehashing page %lu\n", page->base);
      AN_(MD5_CTX) ctx2;
      AN_(MD5_Init)(&ctx2);

      /* TODO: Test fort page->va == uniform_va[MEM_READONLY], however it cannot be
         be done in the same simple way as for MEM_DEFINED since there may be read only pages
         that are not hashed by the generic page hashing */
      if (page->va == uniform_va[MEM_DEFINED]) {
         //AN_(MD5_Update)(&ctx2, (UChar*) page->base, PAGE_SIZE);
         int i;
         for (i = 0; i < REAL_PAGES_IN_PAGE; i++)
         {
             if (page->page_flags[i] == PAGEFLAG_RW) {
                AN_(MD5_Update)(&ctx2, (UChar*) (page->base + VKI_PAGE_SIZE * i), VKI_PAGE_SIZE);
             }
         }
      } else {
         UWord i, j;
         /* This is quite performance critical
          * It needs benchmarking before changing this code */
         UChar *base = (UChar*) page->base;
         SizeT s = 0;
         UChar *b = base;
         SizeT sum = 0;

         for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
             if ((page->page_flags[i] & PAGEFLAG_RW) == PAGEFLAG_RW) {
                 VA *va = page->va;
                 for (j = VKI_PAGE_SIZE * i; j < VKI_PAGE_SIZE * (i + 1); j++)
                     if (va->vabits[j] & MEM_READ_MASK) {
                         if (s == 0) {
                             b = base + j;
                         }
                         s++;
                     } else if (s != 0) {
                         AN_(MD5_Update)(&ctx2, b, s);
                         sum += s;
                         s = 0;
                     }
             }
             if (s != 0) {
                 AN_(MD5_Update)(&ctx2, b, s);
                 sum += s;
                 s = 0;
             }
         }

         if (sum == 0) {
           page->status = EMPTY;
           return;
         }

         if (sum != PAGE_SIZE) {
            AN_(MD5_Update)(&ctx2, page->va->vabits, VA_CHUNKS);
         }
      }
      AN_(MD5_Final)(&page->hash, &ctx2);
      page->status = VALID_HASH;
   }
   if (page->status != EMPTY) {
       AN_(MD5_Update)(ctx, &page->hash, sizeof(MD5_Digest));
   }
}

static void memimage_save_page_content(Page *page)
{
   UWord i, j;
   VA *va = page->va;
   //UWord c = 0;

   if (va == uniform_va[MEM_NOACCESS]) {
      return;
   }

   if (page->data == NULL) {
      page->data = VG_(malloc)("an.page.data", PAGE_SIZE);
   }

   UChar *src = (UChar*) page->base;
   UChar *dst = page->data;

   if (va == uniform_va[MEM_DEFINED] || va == uniform_va[MEM_READONLY]) {
      VG_(memcpy)(dst, src, PAGE_SIZE);
      return;
   }
   for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
      if (page->page_flags[i] & PAGEFLAG_READ) {
         for (j = VKI_PAGE_SIZE * i; j < VKI_PAGE_SIZE * (i + 1); j++) {
            if (va->vabits[j] & MEM_READ_MASK) {
               dst[j] = src[j];
               //c++;
            }
         }
      }
   }
}

static int flags_to_mmap_protection(int flags)
{
    int prot = 0;
    if (flags & PAGEFLAG_READ) {
        prot |= VKI_PROT_READ;
    }

    if (flags & PAGEFLAG_WRITE) {
        prot |= VKI_PROT_WRITE;
    }

    if (flags & PAGEFLAG_EXECUTE) {
        prot |= VKI_PROT_EXEC;
    }
    return prot;
}

static INLINE Int are_all_flags_rw(Page *page) {
    UWord i;
    for (i = 1; i < REAL_PAGES_IN_PAGE; i++) {
        if (page->page_flags[i] != PAGEFLAG_RW) {
            return False;
        }
    }
    return True;
}

static void memimage_restore_page_content(Page *page, Page *old_page)
{
    tl_assert(page->base == old_page->base);
    //page_dump(page);
    VPRINT(2, "memimage_restore_page_content base=%lx\n", page->base);

    if (page->va == uniform_va[MEM_NOACCESS] || page->va == uniform_va[MEM_UNDEFINED]) {
        return;
    }

    UWord i, j;
    UChar *dst = (UChar*) page->base;
    VA *va = page->va;
    UChar *src = page->data;
    tl_assert(src);

    if (va == uniform_va[MEM_DEFINED]) {
        if (are_all_flags_rw(page)) {
            VG_(memcpy)(dst, src, PAGE_SIZE);
            return;
        }
    }
    for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
        int flags = page->page_flags[i];
        int old_flags = old_page->page_flags[i];

        if (flags != old_flags) {
            Addr base = page->base + VKI_PAGE_SIZE * i;
            /* The following code handles only the situation when
             old page is unmapped and new flag is RW,
             other situation needs to be handled separately
          */
            if (flags == PAGEFLAG_UNMAPPED) {
                VPRINT(1, "restore page munmap addr=%lx size=%lu\n", base, VKI_PAGE_SIZE);
                SysRes sr = ML_(am_do_munmap_NO_NOTIFY)(base, VKI_PAGE_SIZE);
                tl_assert(!sr_isError(sr));
                VG_(am_notify_munmap)(base, VKI_PAGE_SIZE);
                continue;
            }

            tl_assert(old_flags == PAGEFLAG_UNMAPPED);
            tl_assert(flags == PAGEFLAG_RW);


            const int mmap_flags = VKI_MAP_PRIVATE | VKI_MAP_FIXED | VKI_MAP_ANONYMOUS;
            const int prot = flags_to_mmap_protection(flags);
            VPRINT(1, "restore page mmap addr=%lx size=%lu page_flags=%d prot=%d\n", base, VKI_PAGE_SIZE, flags, prot);
            SysRes sr = VG_(am_do_mmap_NO_NOTIFY)(base, VKI_PAGE_SIZE, prot, mmap_flags, -1, 0);

            tl_assert(!sr_isError(sr));
            tl_assert(sr._val == base);

            VG_(am_notify_client_mmap)(base, VKI_PAGE_SIZE, prot, mmap_flags, -1, 0);
        }
        if ((flags & PAGEFLAG_RW) == PAGEFLAG_RW) {
            for (j = VKI_PAGE_SIZE * i; j < VKI_PAGE_SIZE * (i + 1); j++) {
                if (va->vabits[j] & MEM_READ_MASK) {
                    dst[j] = src[j];
                }
            }
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
   memimage->answer = current_memspace->answer;
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
    OSet *auxmap = current_memspace->auxmap;
    UWord i = 0;
    AuxMapEnt *elem;

    VG_(OSetGen_ResetIter)(auxmap);
    while(i < memimage->pages_count &&
          (elem = VG_(OSetGen_Next(auxmap)))) {
        Page *page = memimage->pages[i];
        if (LIKELY(page->base == elem->base)) {
            if (elem->page != page) {
                memimage_restore_page_content(page, elem->page);
                page->ref_count++;
                page_dispose(elem->page);
                elem->page = page;
            }
            i++;
        } else {
            tl_assert(page->base > elem->base);
            page_dispose(elem->page);
            elem->page = page_new_empty(elem->base);
        }
    }
    tl_assert(i == memimage->pages_count);
    while ((elem = VG_(OSetGen_Next(auxmap)))) {
        page_dispose(elem->page);
        elem->page = page_new_empty(elem->base);
    }

    VG_(deleteXA)(current_memspace->allocation_blocks);
    current_memspace->allocation_blocks = VG_(cloneXA)("an.allocations",
                                                       memimage->allocation_blocks);
    current_memspace->answer = memimage->answer;

    // Reset cache
    current_memspace->page_cache_size = 0;
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

static Buffer* buffer_new(UWord id, UWord size)
{
   tl_assert(!VG_(HT_lookup)(buffer_table, id));
   stats.buffers_size += size;
   Buffer *buffer = (Buffer*) VG_(malloc)("an.buffers", sizeof(Buffer) + size);
   buffer->next = NULL;
   buffer->id = id;
   buffer->size = size;
   VG_(HT_add_node(buffer_table, buffer));
   return buffer;
}

static void buffer_free(Buffer *buffer)
{
   stats.buffers_size -= buffer->size;
   VG_(HT_remove)(buffer_table, buffer->id);
   VG_(free)(buffer);
}

static void buffer_hash(Buffer *buffer, AN_(MD5_CTX) *ctx)
{
   AN_(MD5_Update)(ctx, (void*) (buffer + 1), buffer->size);
}

INLINE static Buffer *buffer_lookup(UWord id)
{
    Buffer *buffer = (Buffer*) VG_(HT_lookup)(buffer_table, id);
    tl_assert(buffer);
    return buffer;
}

INLINE static Addr buffer_data(Buffer *buffer)
{
    return (Addr) (buffer + 1);
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
   Int lwpid = tst->os_state.lwpid;
   VG_(memcpy)(tst, &state->threadstate, sizeof(ThreadState));
   tst->os_state.lwpid = lwpid;

   /* Restore memory image */
   memimage_restore(&state->memimage);
}

static void prepare_for_write(Addr addr, SizeT size)
{
    if (size == 0) {
        return;
    }
    Addr last_page = start_of_this_page(addr + size - 1);
    addr = start_of_this_page(addr);
    while (addr <= last_page) {
        Page *page = get_page(addr);
        page = page_prepare_for_write_data(page);
        addr += PAGE_SIZE;
    }
}

/* --------------------------------------------------------
 *  Events
 * --------------------------------------------------------*/

static VG_REGPARM(2) void trace_write(Addr addr, SizeT size)
{
   Page *page = get_page_or_null(addr);
   if (UNLIKELY(page == NULL)) {
        report_error_write(addr, size);
        tl_assert(0); // no return here
   }
   page = page_prepare_for_write_data(page);
   VA *va = page->va;
   Addr offset = addr - page->base;
   SizeT i;

   UChar flag = va->vabits[offset];
   SizeT sz = size;
   if (UNLIKELY(offset + sz > PAGE_SIZE)) {
        sz = PAGE_SIZE - offset;
   }

   for (i = 1; i < sz; i++) {
      flag &= va->vabits[offset + i];
   }

   if (UNLIKELY(!(flag & MEM_WRITE_MASK))) {
      report_error_write(addr, size);
      tl_assert(0); // no return here
   }

   if (flag == MEM_UNDEFINED) {
      if (UNLIKELY(va->ref_count >= 2)) {
         va->ref_count--;
         va = va_clone(va);
         page->va = va;
      }
      for (i = 0; i < sz; i++) {
         va->vabits[offset + i] = MEM_DEFINED;
      }
   }

   if (UNLIKELY(sz != size)) {
      trace_write(start_of_this_page(addr) + PAGE_SIZE, size - sz);
   }
}

static VG_REGPARM(2) void trace_read(Addr addr, SizeT size)
{
   Page *page = get_page(addr);
   if (UNLIKELY(page == NULL)) {
        report_error_read(addr, size);
        tl_assert(0); // no return here
   }
   Addr offset = addr - page->base;
   //page_dump(page);

   /* We will check just first byte of address
      to solve problem of partial_loads in functions
      like 'strlen' */

   if (UNLIKELY(!(page->va->vabits[offset] & MEM_READ_MASK))) {
         if (UNLIKELY(page->va->vabits[offset] == MEM_NOACCESS)) {
            report_error_read(addr, size);
            tl_assert(0); // no return here
         }

         SizeT i; // Zero undefined memory before reading
         for (i = 0; i < size; i++) {
             if (page->va->vabits[offset + i] == MEM_UNDEFINED) {
                HChar *d = (HChar*) (offset + i + page->base);
                *d = 0;
             }
         }

   }

   /*
   // Overlap test
   Addr end = (addr & PAGE_MASK) + size;
   if (UNLIKELY(end > PAGE_SIZE)) {
      trace_read(start_of_this_page(addr) + PAGE_SIZE, end - PAGE_SIZE);
   }*/
}

static VG_REGPARM(0) void trace_alu_op(void)
{
    profile.count_instructions++;
}



// This function should be called when write from controller occurs ("WRITE" commands)
static void extern_write(Addr addr, SizeT size, Bool check)
{
    if (check && !check_is_writable(addr, size, NULL)) {
              report_error_write(addr, size);
              tl_assert(0);
    }
    prepare_for_write(addr, size);
    make_mem_defined(addr, size);
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
void read_data(SizeT size, Addr out)
{
    if (message_buffer_size) {
        SizeT s;
        if (message_buffer_size > size) {
            s = size;
        } else {
            s = message_buffer_size;
        }
        VG_(memcpy)((void*)out, message_buffer, message_buffer_size);
        message_buffer_size -= s;
        size -= s;
        out += s;
        if (message_buffer_size) {
            VG_(memmove(message_buffer,
                        message_buffer + s,
                        message_buffer_size));
            return;
        }
    }
    while (size > 0) {
        Int len = VG_(read_socket)(control_socket, (void*) out, size);
        tl_assert(len && len <= size);
        size -= len;
        out += len;
    }
}


static
Bool read_command(char *command)
{
    char *s = message_buffer;
    Int rest = MAX_MESSAGE_BUFFER_LENGTH;
    Int last_read_len = message_buffer_size;
    Int buffer_len = 0;
    Int command_len;

    for(;;) {
       Int i;
       for (i = 0; i < last_read_len; i++) {
             if (*s == '\n') {
                command_len = buffer_len + i;
                buffer_len += last_read_len;
                goto ret;
             }
             s++;
       }

       buffer_len += last_read_len;
       rest -= last_read_len;

       tl_assert(rest > 0); // If fail, command was to long
       last_read_len = VG_(read_socket)(control_socket, s, rest);
       if (UNLIKELY(last_read_len == 0)) {
          return False; // Connection closed
       }
    }

 ret:
    VG_(memcpy(command, message_buffer, command_len));
    command[command_len] = 0;
    message_buffer_size = buffer_len - command_len - 1;
    if (message_buffer_size > 0) {
         VG_(memmove(message_buffer,
                     s + 1,
                     message_buffer_size));
         message_buffer[message_buffer_size] = 0;
    }
    return True;
}

static void put_profile_info(HChar **buffer, SizeT *size)
{
    SizeT s = VG_(snprintf)(*buffer,
                            *size,
                            "PROFILE %lu %lu %lu\n",
                            profile.count_instructions,
                            profile.count_allocations,
                            profile.size_allocations);
    profile.count_instructions = 0;
    profile.count_allocations = 0;
    profile.size_allocations = 0;
    *buffer += s;
    *size -= s;
}


static void write_message(const char *str)
{
   VPRINT(1, "AN%d>> %s", identification, str);

   Int len = VG_(strlen)(str);
   Int r = VG_(write_socket)(control_socket, str, len);
   if (r == -1) {
      VG_(printf)("Connection closed (server)\n");
      VG_(exit)(1);
   }
   tl_assert(r == len);
}

// Same as write_message but with DATA message
static void write_data(void *ptr, SizeT size)
{
   VPRINT(1, "AN%d>> [[ DATA at=%p size=%lu ]]\n", identification, ptr, size);
   char tmp[MAX_MESSAGE_BUFFER_LENGTH];
   /*VG_(snprintf)(tmp, 100, "DATA 1\nX");
   write_message(tmp);*/
   SizeT sz;
   int i = VG_(snprintf)(tmp, MAX_MESSAGE_BUFFER_LENGTH, "DATA %lu\n", size);
   if (size > MAX_MESSAGE_BUFFER_LENGTH - i) {
       sz = MAX_MESSAGE_BUFFER_LENGTH - i;
   } else {
       sz = size;
   }
   VG_(memcpy)(&tmp[i], ptr, sz);
   Int r = VG_(write_socket)(control_socket, tmp, i + sz);
   if (r == -1) {
      VG_(printf)("Connection closed\n");
      VG_(exit)(1);
   }
   tl_assert(r == sz + i);

   if (size - sz > 0) {
       char *p = (char*)ptr;
       r = VG_(write_socket)(control_socket, &p[sz], size - sz);
       if (r == -1) {
          VG_(printf)("Connection closed\n");
          VG_(exit)(1);
       }
       tl_assert(r == size - sz);
   }
}

struct BufferCtrl {
   HChar *buffer;
   int size;
};

static void write_stacktrace_helper(UInt n, Addr ip, void *opaque)
{
   struct BufferCtrl *bc = opaque;
   tl_assert(bc->size > 1);
   const HChar *buf = VG_(describe_IP)(ip, NULL);
   SizeT s = VG_(strlen)(buf);
   tl_assert(s < bc->size);
   VG_(memcpy)(bc->buffer, buf, s);
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
      VG_(printf)("Error: Invalid command\n");
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

static int next_token_int(void) {
   char *str = next_token();
   char *end;
   UWord value = VG_(strtoll10)(str, &end);
   if (*end != '\0') {
      write_message("Error: Invalid argument\n");
      VG_(exit)(1);
   }
   return value;
}


static void process_commands_init(CommandsEnterType cet,
                                  Vg_AislinnCallAnswer *answer) {
   ThreadState *tst = VG_(get_ThreadState)(1);
   tl_assert(tst);
   tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
   tl_assert(cet == CET_SYSCALL || !tst->sched_jmpbuf_valid || cet == CET_REPORT);
   // Reset invalid jmpbuf to make be able generate reasonable hash of state
   // If cet == CET_REPORT then we do not return to program so we dont care about hash
   tst->arch.vex.guest_RDX = 0; // Result of client request
   current_memspace->answer = answer;
}

static void debug_dump_state(UWord state_id)
{
    State *state = (State*) VG_(HT_lookup(state_table, state_id));
    tl_assert(state);
    MemoryImage *image = &state->memimage;
    Page **pages = image->pages;
    VG_(printf)("===== DUMP State %lu =====\n", state_id);
    VG_(printf)("Answer pointer: %p\n", image->answer);

    UWord i;
    for (i = 0; i < image->pages_count; i++) {
        page_dump(pages[i]);
    }


    VG_(printf)("===== END OF DUMP =====\n");

}

static void debug_compare(UWord state_id1, UWord state_id2)
{
    State *state1 = (State*) VG_(HT_lookup(state_table, state_id1));
    MemoryImage *image1 = &state1->memimage;
    Page **pages1 = image1->pages;
    State *state2 = (State*) VG_(HT_lookup(state_table, state_id2));
    MemoryImage *image2 = &state2->memimage;
    Page **pages2 = image2->pages;
    UWord p1 = 0, p2 = 0, i;

    VG_(printf)("Comparing states %lu %lu\n", state_id1, state_id2);

    VG_(printf)("Answer pointers: state1=%p state2=%p\n", image1->answer, image2->answer);

    while (p1 < image1->pages_count && p2 < image2->pages_count) {
        Page *page1 = pages1[p1];
        Page *page2 = pages2[p2];

        if (page1 == page2) {
            p1++;
            p2++;
            continue;
        }

        if (page1->base < page2->base) {
            VG_(printf)("Page %lx: Only in state1\n", page1->base);
            p1++;
            continue;
        }

        if (page1->base > page2->base) {
            VG_(printf)("Page %lx: Only in state2\n", page2->base);
            p2++;
            continue;
        }

        for (i = 0; i < PAGE_SIZE; i++) {
            if (page1->va->vabits[i] != page1->va->vabits[i]) {
                VG_(printf)("%lx: VA state1=%d state2=%d\n",
                            page1->base + i, (int) page1->va->vabits[i],
                                             (int) page2->va->vabits[i]);
            }
            if (page1->va->vabits[i] &&
                page1->data[i] != page2->data[i]) {
                VG_(printf)("%lx: DATA state1=%d state2=%d\n",
                            page1->base + i, (int) page1->data[i],
                                             (int) page2->data[i]);
            }
        }
        p1++;
        p2++;
    }

    while (p1 < image1->pages_count) {
        VG_(printf)("Page %lx: Only in state1\n", pages1[p1]->base);
        p1++;
    }

    while (p2 < image2->pages_count) {
        VG_(printf)("Page %lx: Only in state2\n", pages2[p2]->base);
        p2++;
    }

    SizeT size = sizeof(ThreadArchState);
    //size -= offsetof(VexGuestArchState, guest_RAX);
    UChar *s1 = ((UChar*) &state1->threadstate); // + offsetof(VexGuestArchState, guest_RAX);
    UChar *s2 = ((UChar*) &state2->threadstate); // + offsetof(VexGuestArchState, guest_RAX);
    for (i = 0; i < size; i++) {
        if (s1[i] != s2[i]) {
            VG_(printf)("Arch.vex %lu: %d (%x) %d (%x) words (%lx, %lx)\n",
                        i, s1[i], s1[i], s2[i], s2[i], *((UWord*) &s1[i]), *((UWord*) &s2[i]));
        }
    }

    VG_(printf)("------ End of comparison -----------\n");
}

static void finish_send_buffer(char *buffer, char **position)
{
    SizeT s = ((Addr) *position - (Addr) buffer);
    if (s >= 0) {
        tl_assert(VG_(write_socket)(control_socket, buffer, s) == s);
    }
}

static void add_to_send_buffer(char *buffer, char **position, const void *data, SizeT size)
{
    SizeT s = ((Addr) *position - (Addr) buffer);
    if (s + size <= MAX_MESSAGE_BUFFER_LENGTH) {
        VG_(memcpy)(*position, data, size);
        *position += size;
        return;
    }

    if (s >= 0) {
        finish_send_buffer(buffer, position);
    }
    tl_assert(VG_(write_socket)(control_socket, data, size) == size);
    *position = buffer;
}

static void add_string_to_send_buffer(char *buffer, char **position, const char *str)
{
    SizeT size = VG_(strlen)(str);
    add_to_send_buffer(buffer, position, str, size);
}


static void write_allocations(void)
{
    char output[MAX_MESSAGE_BUFFER_LENGTH];
    char *p = output;
    XArray *a = current_memspace->allocation_blocks;
    SizeT size = VG_(sizeXA)(a) - 1;
    SizeT i;
    for (i = 0; i < size; i++) {
        AllocationBlock *block = VG_(indexXA)(a, i);
        char tmp[100];
        if (block->type == BLOCK_USED) {
            VG_(snprintf(tmp, 100,
                         "%lu %lu|", block->address, block->requested_size));
            add_string_to_send_buffer(output, &p, tmp);
        }
    }
    add_string_to_send_buffer(output, &p, "\n");
    finish_send_buffer(output, &p);
}

static Bool set_capture_syscalls_by_name(const char *name, Bool value)
{
    if (!VG_(strcmp)(name, "write")) {
        capture_syscalls.syscall_write = value;
    } else if (!VG_(strcmp)(name, "read")) {
        capture_syscalls.syscall_read = value;
    } else if (!VG_(strcmp)(name, "open")) {
        capture_syscalls.syscall_open = value;
    } else if (!VG_(strcmp)(name, "close")) {
        capture_syscalls.syscall_close = value;
    } else {
        return False;
    }
    return True;
}

typedef
   struct {
      Int size; // Since Valgrind socket API uses Int, we are using Int, not SizeT
      HChar *buffer;
      Int buffer_size;
      Int socket;
   } SocketWriteBuffer;

static void swb_init(
      SocketWriteBuffer *swb, HChar *buffer, Int buffer_size, Int socket)
{
   swb->size = 0;
   swb->buffer = buffer;
   swb->buffer_size = buffer_size;
   swb->socket = socket;
}

static void* swb_write(SocketWriteBuffer *swb, Int size)
{
   if (swb->size + size >= swb->buffer_size) {
      tl_assert(size <= swb->buffer_size);
      Int send_size = swb->size;
      HChar *send_buffer = swb->buffer;
      tl_assert(send_size > 0);
      do {
          Int written = VG_(write_socket)(swb->socket, send_buffer, send_size);
          tl_assert(written > 0);
          send_size -= written;
          send_buffer += written;
      } while (send_size > 0);;
      swb->size = size;
      return swb->buffer;
   }
   HChar *result = swb->buffer + swb->size;
   swb->size += size;
   return result;
}

static void swb_end(SocketWriteBuffer *swb)
{
   Int written = VG_(write_socket)(swb->socket, swb->buffer, swb->size);
   tl_assert(written == swb->size);
}

typedef
   struct {
      HChar *ptr;
      Int size;
      HChar *buffer;
      Int buffer_size;
      Int socket;
   } SocketReadBuffer;

static void srb_init(
      SocketReadBuffer *srb, void *buffer, SizeT buffer_size, Int socket)
{
   srb->ptr = (HChar*) buffer;
   srb->buffer = (HChar*) buffer;
   srb->buffer_size = buffer_size;
   srb->socket = socket;
   srb->size = VG_(read_socket)(socket, buffer, buffer_size);
   tl_assert(srb->size > 0);
}

static void* srb_read(SocketReadBuffer *srb, Int size)
{
   Int remaining = srb->size - (srb->ptr - srb->buffer);
   if (remaining < size) {
      tl_assert(size <= srb->buffer_size);
      VG_(memmove)(srb->buffer, srb->ptr, remaining);
      srb->size = remaining;
      do {
         Int read = VG_(read_socket)(srb->socket, &srb->buffer[srb->size], srb->buffer_size - srb->size);
         tl_assert(read > 0);
         srb->size += read;
      } while(srb->size < size);
      srb->ptr = srb->buffer + size;
      return srb->buffer;
   }
   HChar *result = srb->ptr;
   srb->ptr += size;
   return result;
}

static void push_page(SocketWriteBuffer *swb, Page *page)
{
   TransportPageHeader *page_header = (TransportPageHeader *)
         swb_write(swb, sizeof(TransportPageHeader));
   VA *va = page->va;
   page_header->base = page->base;
   //page_header[i].hash = state->memimage.pages[i]->hash;
   Int i;
   Bool transport_page[REAL_PAGES_IN_PAGE];
   Bool transport_va[REAL_PAGES_IN_PAGE];
   Int size = 0;
   for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
      transport_page[i] = False;
      transport_va[i] = False;
      page_header->flags[i] = page->page_flags[i];

      if (page->page_flags[i] == PAGEFLAG_UNMAPPED) {
          page_header->flags[i] = PAGEFLAG_UNMAPPED | TRANSPORT_PAGEFLAG_NOACCESS;
          continue;
      }
      if (page->page_flags[i] != PAGEFLAG_RW) {
          transport_va[i] = True;
          page_header->flags[i] = page->page_flags[i] | TRANSPORT_PAGEFLAG_VAONLY;
          size += VKI_PAGE_SIZE;
          continue;
      }
      Int j;
      Int offset = i * VKI_PAGE_SIZE;
      UChar perm = va->vabits[offset];
      for (j = 1; j < VKI_PAGE_SIZE; j++) {
          if (va->vabits[offset + j] != perm) {
              break;
          }
      }

      if (j == VKI_PAGE_SIZE) {
          if (perm == MEM_DEFINED) {
              page_header->flags[i] |= TRANSPORT_PAGEFLAG_DEFINED;
              size += VKI_PAGE_SIZE;
              transport_page[i] = True;
          } else if (perm == MEM_NOACCESS) {
              page_header->flags[i] |= TRANSPORT_PAGEFLAG_NOACCESS;
          } else if (perm == MEM_UNDEFINED) {
              page_header->flags[i] |= TRANSPORT_PAGEFLAG_UNDEFINED;
          } else if (perm == MEM_READONLY) {
              page_header->flags[i] |= TRANSPORT_PAGEFLAG_READONLY;
              size += VKI_PAGE_SIZE;
              transport_page[i] = True;
          } else {
              tl_assert(0);
          }
      } else {
          page_header->flags[i] |= TRANSPORT_PAGEFLAG_FULL;
          size += 2 * VKI_PAGE_SIZE;
          transport_page[i] = True;
          transport_va[i] = True;
      }
   }

   UChar *data = (UChar*) swb_write(swb, size);

   for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
       if (transport_va[i]) {
          VG_(memcpy)(data, &va->vabits[i * VKI_PAGE_SIZE], VKI_PAGE_SIZE);
          data += VKI_PAGE_SIZE;
       }
   }

   for (i = 0; i < REAL_PAGES_IN_PAGE; i++) {
       if (transport_page[i]) {
          VG_(memcpy)(data, &page->data[i * VKI_PAGE_SIZE], VKI_PAGE_SIZE);
          data += VKI_PAGE_SIZE;
       }
   }
}

static void push_state(Int socket, State *state)
{
   SocketWriteBuffer swb;
   Int buffer_size = 160 * 1024;
   void *buffer = VG_(malloc)("an.srb", buffer_size);
   swb_init(&swb, buffer, buffer_size, socket);

   Word blocks_count;
   void *blocks_ptr;
   VG_(getContentsXA_UNSAFE)(state->memimage.allocation_blocks, &blocks_ptr, &blocks_count);

   TransportStateHeader *header = swb_write(&swb, sizeof(TransportStateHeader));
   UWord pages_count = state->memimage.pages_count;
   header->pages_count = pages_count;
   header->allocation_blocks_count = blocks_count;
   header->answer = state->memimage.answer;
   header->threadstate = state->threadstate;

   AllocationBlock *blocks = swb_write(&swb, sizeof(AllocationBlock) * blocks_count);
   VG_(memcpy)(blocks, blocks_ptr, sizeof(AllocationBlock) * blocks_count);


   UWord i;
   for (i = 0; i < pages_count; i++) {
      Page *page = state->memimage.pages[i];
      push_page(&swb, page);

   }
   swb_end(&swb);
   VG_(free)(buffer);
}

static Page *pull_page(SocketReadBuffer *srb)
{
    TransportPageHeader *page_header =
          (TransportPageHeader*) srb_read(srb, sizeof(TransportPageHeader));
    tl_assert(page_header->base % PAGE_SIZE == 0);
    Page *page = page_new(page_header->base);
    page->status = INVALID_HASH;

    Int j;

    // This forces to create a page in current_memspace if not present
    get_page(page->base);


    Int flags[REAL_PAGES_IN_PAGE];

    page->data = VG_(malloc)("an.page.data", PAGE_SIZE);

    Bool defined = True;
    Bool rdonly = True;
    Bool noaccess = True;
    Bool undefined = True;

    // Copy flags, because srb_read may overwrite header;
    for (j = 0; j < REAL_PAGES_IN_PAGE; j++) {
         Int flag = page_header->flags[j];
         flags[j] = flag;
         page->page_flags[j] = flag & ~TRANSPORT_PAGEFLAG_MASK;
         Int mflag = flag & TRANSPORT_PAGEFLAG_MASK;
         if (mflag != TRANSPORT_PAGEFLAG_DEFINED) {
            defined = False;
         }
         if (mflag != TRANSPORT_PAGEFLAG_READONLY) {
            rdonly = False;
         }
         if (mflag != TRANSPORT_PAGEFLAG_NOACCESS) {
            noaccess = False;
         }
         if (mflag != TRANSPORT_PAGEFLAG_UNDEFINED) {
            undefined = False;
         }
    }

    if (defined) {
       page->va = uniform_va[MEM_DEFINED];
       page->va->ref_count++;
       VG_(memcpy)(page->data,
                   srb_read(srb, PAGE_SIZE),
                   PAGE_SIZE);
       return page;
    }

    if (noaccess) {
       page->va = uniform_va[MEM_NOACCESS];
       page->va->ref_count++;
       VG_(memset)(page->data, 0, PAGE_SIZE);
       return page;
    }

    if (undefined) {
       page->va = uniform_va[MEM_UNDEFINED];
       page->va->ref_count++;
       VG_(memset)(page->data, 0, PAGE_SIZE);
       return page;
    }

    if (rdonly) {
       page->va = uniform_va[MEM_READONLY];
       page->va->ref_count++;
       VG_(memcpy)(page->data,
                   srb_read(srb, PAGE_SIZE),
                   PAGE_SIZE);
       return page;
    }

    page->va = va_new();

    for (j = 0; j < REAL_PAGES_IN_PAGE; j++) {
        Int offset = VKI_PAGE_SIZE * j;
        Int flag = flags[j];
        switch (flag & TRANSPORT_PAGEFLAG_MASK) {
            case TRANSPORT_PAGEFLAG_DEFINED:
                VG_(memset)(&page->va->vabits[offset], MEM_DEFINED, VKI_PAGE_SIZE);
                break;
            case TRANSPORT_PAGEFLAG_NOACCESS:
                VG_(memset)(&page->va->vabits[offset], MEM_NOACCESS, VKI_PAGE_SIZE);
                break;
            case TRANSPORT_PAGEFLAG_UNDEFINED:
                VG_(memset)(&page->va->vabits[offset], MEM_UNDEFINED, VKI_PAGE_SIZE);
                break;
           case TRANSPORT_PAGEFLAG_READONLY:
               VG_(memset)(&page->va->vabits[offset], MEM_READONLY, VKI_PAGE_SIZE);
               break;
           case TRANSPORT_PAGEFLAG_VAONLY:
           case TRANSPORT_PAGEFLAG_FULL:
               VG_(memcpy)(&page->va->vabits[offset],
                           srb_read(srb, VKI_PAGE_SIZE),
                           VKI_PAGE_SIZE);
              break;
           default:
              break;
        }
    }

    for (j = 0; j < REAL_PAGES_IN_PAGE; j++) {
        Int flag = flags[j] & TRANSPORT_PAGEFLAG_MASK;
        if (flag != TRANSPORT_PAGEFLAG_NOACCESS
            && flag != TRANSPORT_PAGEFLAG_VAONLY
            && flag != TRANSPORT_PAGEFLAG_UNDEFINED) {
            VG_(memcpy)(&page->data[j * VKI_PAGE_SIZE],
                  srb_read(srb, VKI_PAGE_SIZE),
                  VKI_PAGE_SIZE);
        } else {
           VG_(memset(&page->data[j * VKI_PAGE_SIZE], 0, VKI_PAGE_SIZE));
        }
    }
    return page;
}

static State* pull_state(Int socket, UWord state_id)
{
   State *state = VG_(malloc)("an.state", sizeof(State));
   VG_(memset)(state, 0, sizeof(State));

   SocketReadBuffer srb;
   const Int buffer_size = 160 * 1024;
   void *buffer = VG_(malloc)("an.srb", buffer_size);
   srb_init(&srb, buffer, buffer_size, socket);

   TransportStateHeader *header = (TransportStateHeader*)
      srb_read(&srb, sizeof(TransportStateHeader));

   state->id = state_id;
   state->memimage.pages_count = header->pages_count;
   state->memimage.answer = header->answer;
   state->threadstate = header->threadstate;

   Word pages_count = header->pages_count;
   Word blocks_count = header->allocation_blocks_count;

   Page **pages = (Page**) VG_(malloc)("an.memimage", pages_count * sizeof(Page*));
   state->memimage.pages = pages;

   state->memimage.allocation_blocks = VG_(newXA) \
          (VG_(malloc), "an.allocations", VG_(free), sizeof(AllocationBlock));

   VG_(hintSizeXA)(state->memimage.allocation_blocks, blocks_count);
   AllocationBlock *blocks = \
         (AllocationBlock*) srb_read(&srb, sizeof(AllocationBlock) * blocks_count);
   Int i;
   for (i = 0; i < blocks_count; i++) {
      VG_(addToXA)(state->memimage.allocation_blocks, &blocks[i]);
   }

   for (i = 0; i < pages_count; i++) {
        pages[i] = pull_page(&srb);
   }
   VG_(free)(buffer);
   return state;
}

static
void process_commands(CommandsEnterType cet, Vg_AislinnCallAnswer *answer)
{
   process_commands_init(cet, answer);
   char command[MAX_MESSAGE_BUFFER_LENGTH + 1];

   if (answer) {
        answer->function = NULL;
   }

   for (;;) {
      if (!read_command(command)) {
         VG_(exit)(1);
      }
      VPRINT(1, "AN%d<< %s\n", identification, command);
      char *cmd = VG_(strtok(command, " "));

      if (!VG_(strcmp(cmd, "SAVE"))) {
         tl_assert(cet != CET_SYSCALL);
         State *state = state_save_current();
         VG_(HT_add_node(state_table, state));
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH, "%lu\n", state->id));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp)(cmd, "RESTORE")) {
         tl_assert(cet != CET_SYSCALL);
         UWord state_id = next_token_uword();

         State *state = (State*) VG_(HT_lookup(state_table, state_id));
         if (state == NULL) {
            write_message("Error: State not found\n");
         }
         state_restore(state);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp)(cmd, "WRITE")) {
         Bool check = !VG_(strcmp)("check", next_token());
         Addr addr = next_token_uword();
         char *param = next_token();
         if (!VG_(strcmp)(param, "int")) {
            extern_write((Addr)addr, sizeof(int), check);
            *((Int*) addr) = next_token_int();
         } else if (!VG_(strcmp)(param, "ints")) {
               SizeT i, s = next_token_uword();
               extern_write(addr, s * sizeof(int), check);
               Int *a = (Int *) addr;
               for (i = 0; i < s; i++) {
                  *a = next_token_int();
                  a++;
               }
         } else if (!VG_(strcmp)(param, "pointer")) {
             extern_write(addr, sizeof(Addr), check);
             *((Addr*) addr) = next_token_uword();
         } else if (!VG_(strcmp(param, "buffer"))) {
            UWord buffer_id = next_token_uword();
            Buffer *buffer = buffer_lookup(buffer_id);
            extern_write((Addr)addr, buffer->size, check);
            VG_(memcpy((void*) addr, (void*) buffer_data(buffer), buffer->size));
         } else if (!VG_(strcmp(param, "buffer-part"))) {
            UWord buffer_id = next_token_uword();
            Buffer *buffer = buffer_lookup(buffer_id);
            UWord index = (UWord) next_token_uword();
            UWord size = (UWord) next_token_uword();
            extern_write((Addr)addr, size, check);
            VG_(memcpy((void*) addr, (void*) (buffer_data(buffer) + index), size));
         } else if (!VG_(strcmp(param, "addr"))) {
            Addr source = (Addr) next_token_uword();
            UWord size = (UWord) next_token_uword();
            extern_write((Addr)addr, size, check);
            VG_(memcpy((void*) addr, (void*) source, size));
         } else if (!VG_(strcmp)(param, "mem")) {
             SizeT size = next_token_uword();
             extern_write(addr, size, check);
             read_data(size, addr);
         } else if (!VG_(strcmp)(param, "string")) {
             char *s = next_token();
             extern_write(addr, VG_(strlen)(s) + 1, check);
             VG_(strcpy)((void*)addr, s);
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
            VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH,
                         "%d\n", *((Int*) addr));
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
         } else if (!VG_(strcmp)(param, "pointer")) {
                VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH,
                             "%lu\n", *((Addr*) addr));
         } else if(!VG_(strcmp)(param, "pointers")) {
                UWord count = next_token_uword();
                UWord written = 0;
                UWord i;
                Addr *iaddr = addr;
                for (i = 0; i < count; i++) {
                   written += VG_(snprintf)(command + written,
                                            MAX_MESSAGE_BUFFER_LENGTH - written,
                                            "%lu ", *iaddr);
                   iaddr += 1;
                }
                written += VG_(snprintf)(command + written,
                                         MAX_MESSAGE_BUFFER_LENGTH - written,
                                         "\n");
                tl_assert(written < MAX_MESSAGE_BUFFER_LENGTH);
         } else if(!VG_(strcmp)(param, "mem")) {
                SizeT size = next_token_uword();
                write_data(addr, size);
                continue; // we want to skip "write_message" at the end of switch
         } else if(!VG_(strcmp)(param, "string")) {
                write_data(addr, VG_(strlen)(addr));
                continue; // we want to skip "write_message" at the end of switch
         } else {
                tl_assert(0);
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
         tl_assert(cet == CET_SYSCALL || !tst->sched_jmpbuf_valid);

         if (cet == CET_FINISH) { // Thread finished, so after restore, status has to be fixed
            tst->status = VgTs_Init;
         }
         return;
      }

      if (!VG_(strcmp(cmd, "RUN_DROP_SYSCALL"))) {
         tl_assert(cet == CET_SYSCALL);
         tl_assert(!capture_syscalls.drop_current_syscall);
         capture_syscalls.drop_current_syscall = True;
         capture_syscalls.return_value = next_token_uword();
         return;
      }

      if (!VG_(strcmp(cmd, "RUN_FUNCTION"))) {
         if (UNLIKELY(current_memspace->answer == NULL)) {
            VG_(printf)("Function cannot be called from this context\n");
            VG_(exit)(1);
         }
         ThreadState *tst = VG_(get_ThreadState)(1);
         tl_assert(tst);
         tl_assert(tst->sig_queue == NULL); // TODO: handle non null sig_qeue
         tl_assert(!tst->sched_jmpbuf_valid || cet == CET_REPORT);

         if (cet == CET_FINISH) { // Thread finished, so after restore, status has to be fixed
            tst->status = VgTs_Init;
         }

         current_memspace->answer->function = (void*) next_token_uword();
         current_memspace->answer->function_type = next_token_uword();
         UWord count = next_token_uword();
         tl_assert(count <= 6);
         UWord i;
         for (i = 0; i < count; i++) {
             current_memspace->answer->args[i] = next_token_uword();
         }
         return;
      }

      if (!VG_(strcmp(cmd, "READ_BUFFER"))) {
            UWord id = next_token_uword();
            Buffer *buffer = buffer_lookup(id);
            write_data((void*)buffer_data(buffer), buffer->size);
            continue; // we want to skip "write_message" at the end of switch
      }

      if (!VG_(strcmp(cmd, "WRITE_BUFFER"))) {
         UWord buffer_id = (UWord) next_token_uword();
         UWord index = (UWord) next_token_uword();
         Addr addr = (Addr) next_token_uword();
         UWord size = (UWord) next_token_uword();
         Buffer *buffer = buffer_lookup(buffer_id);
         VG_(memcpy)((void*) (buffer_data(buffer) + index), (void*) addr, size);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "WRITE_BUFFER_DATA"))) {
         UWord buffer_id = (UWord) next_token_uword();
         UWord index = (UWord) next_token_uword();
         UWord size = (UWord) next_token_uword();
         Buffer *buffer = buffer_lookup(buffer_id);
         read_data(size, buffer_data(buffer) + index);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "NEW_BUFFER"))) { // Create buffer
         UWord id = next_token_uword();
         UWord size = next_token_uword();
         buffer_new(id, size);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "HASH_BUFFER"))) {
         UWord buffer_id = (UWord) next_token_uword();
         Buffer *buffer = buffer_lookup(buffer_id);
         MD5_Digest digest;
         char digest_str[33]; // 16 * 2 + 1
         AN_(MD5_CTX) ctx;
         AN_(MD5_Init)(&ctx);
         buffer_hash(buffer, &ctx);
         AN_(MD5_Final)(&digest, &ctx);
         hash_to_string(&digest, digest_str);
         VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%s\n", digest_str);
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "FREE_BUFFER"))) { // free buffer
         UWord buffer_id =  next_token_uword();
         Buffer *buffer = buffer_lookup(buffer_id);
         buffer_free(buffer);
         //write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "HASH"))) {
         tl_assert(cet != CET_SYSCALL);
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

         State *state = (State*) VG_(HT_lookup(state_table, state_id));
         if (state == NULL) {
            write_message("Error: State not found\n");
            VG_(exit)(1);
         }
         VG_(HT_remove)(state_table, state_id);
         state_free(state);
         //write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp)(cmd, "CHECK")) {
          char *type = next_token();
          Addr addr = next_token_uword();
          SizeT size = next_token_uword();
          Bool result;
          Addr first_invalid_addr;
          if (!VG_(strcmp)(type, "write")) {
              result = check_is_writable(addr, size, &first_invalid_addr);
          } else if (!VG_(strcmp)(type, "read")) {
              result = check_is_readable(addr, size, &first_invalid_addr);
          } else {
              write_message("Error: Invalid argument\n");
              VG_(exit)(1);
          }

          if (result) {
               write_message("Ok\n");
          } else {
              VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                           "%lu\n", first_invalid_addr));
              write_message(command);
          }
          continue;
      }

      if (!VG_(strcmp)(cmd, "LOCK")) {
          Addr addr = next_token_uword();
          SizeT size = next_token_uword();
          fill_undefined_memory(addr, size);
          make_mem_readonly(addr, size);
          write_message("Ok\n");
          continue;
      }

      if (!VG_(strcmp)(cmd, "UNLOCK")) {
          Addr addr = next_token_uword();
          SizeT size = next_token_uword();
          make_mem_defined(addr, size);
          write_message("Ok\n");
          continue;
      }

      if (!VG_(strcmp)(cmd, "STATS")) {
          VG_(snprintf)(command,
                        MAX_MESSAGE_BUFFER_LENGTH,
                        "pages %ld|"
                        "vas %ld|"
                        "active-pages %ld|"
                        "buffers-size %lu\n",
                        stats.pages,
                        stats.vas,
                        VG_(OSetGen_Size)(current_memspace->auxmap),
                        stats.buffers_size);
          write_message(command);
          continue;
      }

      if (!VG_(strcmp)(cmd, "ALLOCATIONS")) {
          write_allocations();
          continue;
      }

      if (!VG_(strcmp(cmd, "CLIENT_MALLOC"))) {
         UWord size = next_token_uword();
         void* buffer = client_malloc(0, size);
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%lu\n", (UWord) buffer));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "CLIENT_MALLOC_FROM_BUFFER"))) {
         UWord buffer_id = next_token_uword();
         Buffer *buffer = buffer_lookup(buffer_id);
         SizeT size = buffer->size;
         void *mem = client_malloc(0, size);
         extern_write((Addr)mem, size, False);
         VG_(memcpy(mem, buffer + 1, size));
         VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH,
                      "%lu\n", (UWord) mem));
         write_message(command);
         continue;
      }

      if (!VG_(strcmp(cmd, "CLIENT_FREE"))) {
         Addr mem = next_token_uword();
         client_free(0, (void*) mem);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "CONN_PUSH_STATE"))) {
        Int socket = next_token_int();
        UWord state_id = next_token_uword();
        State *state = (State*) VG_(HT_lookup(state_table, state_id));
        tl_assert(state);
        push_state(socket, state);
        continue;
      }

      if (!VG_(strcmp(cmd, "CONN_PULL_STATE"))) {
        Int socket = next_token_int();
        UWord state_id = make_new_id();
        State *state = pull_state(socket, state_id);
        VG_(HT_add_node(state_table, state));
        VG_(snprintf(command, MAX_MESSAGE_BUFFER_LENGTH, "%lu\n", state->id));
        write_message(command);
        continue;
      }

      if (!VG_(strcmp(cmd, "CONN_LISTEN"))) {
        Int socket = VG_(make_listen_socket(0, 1));
        struct vki_sockaddr_in name;
        Int size = sizeof(name);
        tl_assert(VG_(getsockname)(socket, (struct vki_sockaddr*) &name, &size) == 0);
        Int port = VG_(ntohs)(name.sin_port);
        VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH, "%d\n", port);
        write_message(command);
        int client_socket = VG_(accept)(socket, NULL, NULL);
        tl_assert(client_socket >= 0);
        VG_(close)(socket);
        VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH, "%d\n", client_socket);
        write_message(command);
        continue;
      }

      if (!VG_(strcmp(cmd, "CONN_CONNECT"))) {
        char *param = next_token();
        Int socket = VG_(connect_via_socket)(param);
        VG_(snprintf)(command, MAX_MESSAGE_BUFFER_LENGTH, "%d\n", socket);
        write_message(command);
        continue;
      }

      if (!VG_(strcmp(cmd, "QUIT"))) {
         VG_(exit)(1);
      }

      if (!VG_(strcmp(cmd, "SET"))) {
         char *param = next_token();
         if (!VG_(strcmp)(param, "syscall")) {
             param = next_token();
             Bool value = !VG_(strcmp)(next_token(), "on");
             if (set_capture_syscalls_by_name(param, value)) {
                 write_message("Ok\n");
                 continue;
             }
         }
         write_message("Error: Invalid argument\n");
         VG_(exit)(1);
      }

      if (!VG_(strcmp(cmd, "DEBUG_DUMP_STATE"))) {
         UWord state_id = next_token_uword();
         debug_dump_state(state_id);
         write_message("Ok\n");
         continue;
      }

      if (!VG_(strcmp(cmd, "DEBUG_COMPARE"))) {
            UWord state1 = next_token_uword();
            UWord state2 = next_token_uword();
            debug_compare(state1, state2);
            write_message("Ok\n");
            continue;
      }
      write_message("Error: Unknown command:");
      write_message(command);
      write_message("\n");
   }
}

/* --------------------------------------------------------
 *  CALLBACKS
 */

static
Bool an_handle_client_request ( ThreadId tid, UWord* arg, UWord* ret )
{
   Vg_AislinnCallAnswer *answer = NULL;
   CommandsEnterType cet;

   tl_assert(tid == 1); // No multithreading supported yet
   *ret = 0;

   if (!VG_IS_TOOL_USERREQ('A','N',arg[0])) {
        return False;
   }

   char message[MAX_MESSAGE_BUFFER_LENGTH + 1];
   tl_assert(arg[1]);
   switch(arg[0]) {
      case VG_USERREQ__AISLINN_CALL: {
         SizeT l = MAX_MESSAGE_BUFFER_LENGTH - 1; // reserve 1 char for \n
         UWord i;
         char *m = message;
         if (profile.enable) {
            put_profile_info(&m, &l);
         }
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
         answer = (Vg_AislinnCallAnswer*) arg[4];
         cet = CET_CALL;
       } break;
       case VG_USERREQ__AISLINN_FUNCTION_RETURN: {
          answer = (Vg_AislinnCallAnswer*) arg[1];
          VG_(strcpy)(message, "FUNCTION_FINISH\n");
          cet = CET_CALL;
        } break;
      default:
         tl_assert(0);
   }

   write_message(message);
   process_commands(cet, answer);
   return True;
}

static int make_page_flags(Bool rr, Bool ww, Bool xx)
{
    int flags = PAGEFLAG_MAPPED;
    if (rr) {
        flags |= PAGEFLAG_READ;
    }
    if (ww) {
        flags |= PAGEFLAG_WRITE;
    }
    if (xx) {
        flags |= PAGEFLAG_EXECUTE;
    }
    return flags;
}


static
void new_mem_mmap (Addr a, SizeT len, Bool rr, Bool ww, Bool xx,
                   ULong di_handle)
{
   VPRINT(2, "new_mem_mmap %lx-%lx %lu %d %d %d\n", a, a + len, len, rr, ww, xx);

   if (rr && ww) {
      make_mem_defined(a, len);
   } else if (rr) {
      make_mem_readonly(a, len);
   } else {
      make_mem_noaccess(a, len);
   }

   set_address_range_page_flags(a, len, make_page_flags(rr, ww, xx));

   //memspace_dump();
}

static
void new_mem_mprotect ( Addr a, SizeT len, Bool rr, Bool ww, Bool xx )
{
   VPRINT(2, "new_mem_mprotect %lx-%lx %lu %d %d %d\n", a, a + len, len, rr, ww, xx);

   if (rr && ww) {
       make_mem_undefined(a, len);
   } else if (rr) {
      make_mem_readonly(a, len);
   } else {
      make_mem_noaccess(a, len);
   }
   set_address_range_page_flags(a, len, make_page_flags(rr, ww, xx));
}

static
void mem_unmap(Addr a, SizeT len)
{
   VPRINT(2, "unmap %lx-%lx %lu\n", a, a + len, len);

   make_mem_noaccess(a, len);
   set_address_range_page_flags(a, len, PAGEFLAG_UNMAPPED);
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
   VPRINT(2, "new_mem_startup %lx-%lx %lu %d %d %d\n", a, a + len, len, rr, ww, xx);
   if (rr && ww) {
      make_mem_defined(a, len);
   } else if (rr) {
      make_mem_readonly(a, len);
   } else {
      make_mem_noaccess(a, len);
   }
   Addr offset = a % VKI_PAGE_SIZE;
   set_address_range_page_flags(a - offset, len + offset, make_page_flags(rr, ww, xx));
}

static void new_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("NEW STACK %lx %lu\n", a - VG_STACK_REDZONE_SZB, len);
   /* When undefined memory trackig will work, then hashing will ignore these values
    * now we reset new stack content to zero to have more deterministic memory
    * and therefore more equivalent states will have same hash */
   //VG_(memset)((void*) (a - VG_STACK_REDZONE_SZB), 0, len);
   make_mem_undefined(a - VG_STACK_REDZONE_SZB, len);
}

static
void new_mem_stack_signal(Addr a, SizeT len, ThreadId tid)
{
   //VG_(printf)("STACK SIGNAL %lx %lu", a - VG_STACK_REDZONE_SZB, len);
   /* Same reason for reseting stack as in new_mem_stack */

   VG_(memset)((void*) (a - VG_STACK_REDZONE_SZB), 0, len);
   make_mem_undefined(a - VG_STACK_REDZONE_SZB, len);
}

static void die_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("DIE STACK %lx %lu\n", a - VG_STACK_REDZONE_SZB, len);
   make_mem_noaccess(a - VG_STACK_REDZONE_SZB, len);
}

static void ban_mem_stack (Addr a, SizeT len)
{
   //VG_(printf)("BAN STACK %lx %lu\n", a - VG_STACK_REDZONE_SZB, len);
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

   state_table = VG_(HT_construct)("an.states");
   buffer_table = VG_(HT_construct)("an.buffers");
   uniform_va[MEM_NOACCESS] = va_new();
   VG_(memset)(uniform_va[MEM_NOACCESS]->vabits, MEM_NOACCESS, VA_CHUNKS);
   uniform_va[MEM_UNDEFINED] = va_new();
   VG_(memset)(uniform_va[MEM_UNDEFINED]->vabits, MEM_UNDEFINED, VA_CHUNKS);
   uniform_va[MEM_READONLY] = va_new();
   VG_(memset)(uniform_va[MEM_READONLY]->vabits, MEM_READONLY, VA_CHUNKS);
   uniform_va[MEM_DEFINED] = va_new();
   VG_(memset)(uniform_va[MEM_DEFINED]->vabits, MEM_DEFINED, VA_CHUNKS);
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
   HChar str[MAX_MESSAGE_BUFFER_LENGTH];
   SizeT l = MAX_MESSAGE_BUFFER_LENGTH;
   HChar *buffer = str;
   if (profile.enable) {
       put_profile_info(&buffer, &l);
   }
   VG_(snprintf)(buffer, l, "EXIT %lu\n", tst->os_state.exitcode);
   write_message(str);
   process_commands(CET_FINISH, NULL);
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
void event_read(IRSB *sb, IRExpr *addr, Int dsize)
{
   IRExpr **args = mkIRExprVec_2(addr, mkIRExpr_HWord(dsize));
   IRDirty *di   = unsafeIRDirty_0_N( /*regparms*/2,
                             "trace_read", VG_(fnptr_to_fnentry)(trace_read),
                             args);
   addStmtToIRSB( sb, IRStmt_Dirty(di) );
}

static
void event_alu_op(IRSB *sb, IRExpr *op)
{
    IRExpr **args = mkIRExprVec_0();
    IRDirty *di   = unsafeIRDirty_0_N( /*regparms*/0,
                              "trace_alu_op", VG_(fnptr_to_fnentry)(trace_alu_op),
                              args);
    addStmtToIRSB( sb, IRStmt_Dirty(di) );

}

static
IRSB* an_instrument ( VgCallbackClosure* closure,
                      IRSB* sb_in,
                      const VexGuestLayout* layout,
                      const VexGuestExtents* vge,
                      const VexArchInfo* archinfo_host,
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

         case Ist_WrTmp: {
            IRExpr* data = st->Ist.WrTmp.data;
            switch (data->tag) {
                case Iex_Load:
                    event_read(sb_out,
                               data->Iex.Load.addr,
                               sizeofIRType(data->Iex.Load.ty));
                    break;
                case Iex_Unop:
                case Iex_Binop:
                case Iex_Triop:
                case Iex_Qop:
                case Iex_ITE:
                    if (profile.enable) {
                        event_alu_op(sb_out, data);
                    }
                    break;
                default:
                    break;
            }
            addStmtToIRSB(sb_out, st);
            break;
         }

         case Ist_Store: {
            IRExpr* data = st->Ist.Store.data;
            IRType  type = typeOfIRExpr(tyenv, data);
            tl_assert(type != Ity_INVALID);
            event_write(sb_out, st->Ist.Store.addr, sizeofIRType(type));
            addStmtToIRSB(sb_out, st);
            break;
         }

         case Ist_StoreG: {
            VG_(printf)("Ist_StoreG not implemented yet\n");
            VG_(exit)(0);
         }

         case Ist_CAS: {
              IRType type;
              IRCAS* cas = st->Ist.CAS.details;
              tl_assert(cas->addr != NULL);
              tl_assert(cas->dataLo != NULL);
              type = typeOfIRExpr(tyenv, cas->dataLo);
              event_write(sb_out, cas->addr, sizeofIRType(type));
              addStmtToIRSB(sb_out, st);
              break;
         }

         case Ist_LLSC: {
              VG_(printf)("Ist_StoreG not implemented yet\n");
              VG_(exit)(0);
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
   const char *syscall_name;

   if (VG_INT_CLO(arg, "--port", server_port)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--verbose", verbosity_level)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--identification", identification)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--heap-size", heap_max_size)) {
      return True;
   }

   if (VG_INT_CLO(arg, "--alloc-redzone-size", redzone_size)) {
      return True;
   }

   if (VG_STR_CLO(arg, "--capture-syscall", syscall_name)) {
      return set_capture_syscalls_by_name(syscall_name, True);
   }

   if (VG_BOOL_CLO(arg, "--profile", profile.enable)) {
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
    Addr addr = memspace_alloc(n, 1);
    VG_(memset)((void*)addr, 0, n);
    make_mem_undefined(addr, n);
    VPRINT(2, "client_malloc address=%lx size=%lu\n", addr, n);
    return (void*) addr;
}

static
void* user_memalign (ThreadId tid, SizeT alignB, SizeT n)
{
    Addr addr = memspace_alloc(n, alignB);
    VG_(memset)((void*)addr, 0, n);
    make_mem_undefined(addr, n);
    VPRINT(2, "client_memalign address=%lx size=%lu\n", addr, n);
    return (void*) addr;
}

static
void* user_calloc (ThreadId tid, SizeT nmemb, SizeT size1)
{
    SizeT size = nmemb *size1;
    Addr addr = memspace_alloc(size, 1);
    VG_(memset)((void*)addr, 0, size);
    make_mem_defined(addr, size);
    VPRINT(2, "client_calloc address=%lx size=%lu\n", addr, size);
    return (void*) addr;
}

static
void* user_realloc(ThreadId tid, void* p_old, SizeT new_szB)
{
    Addr addr = memspace_alloc(new_szB, 1);
    // TODO: We should properly copy VA values from the original block
    make_mem_defined(addr, new_szB);
    VPRINT(2, "client_realloc address=%lx size=%lu\n", addr, new_szB);
    if (p_old == NULL) {
        VG_(memset)((void*)addr, 0, new_szB);
        return (void*) addr;
    }
    SizeT s = memspace_block_size((Addr) p_old);
    VG_(memcpy)((void*)addr, p_old, s);
    if (new_szB > s) {
        VG_(memset)((void*)(addr + s), 0, new_szB - s);
    }
    return (void*) addr;
}

static
SizeT client_malloc_usable_size(ThreadId tid, void* p)
{
    VG_(tool_panic)("client_malloc_usable_size: Not implemented");
}


static void client_free (ThreadId tid, void *a)
{
    VPRINT(2, "client_free %lx\n", (Addr) a);
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

static
Bool syscall_control(ThreadId tid, UInt syscallno,
                      UWord* args, UInt nArgs, SysRes *sysres)
{
    const char *name = NULL;
    UInt count = 0;

    switch (syscallno) {
      case __NR_write:
          if (!capture_syscalls.syscall_write) {
              return True;
          }
          name = "write";
          count = 3;
          break;
       case __NR_read:
           if (!capture_syscalls.syscall_read) {
               return True;
           }
           name = "read";
           count = 3;
           break;
       case __NR_open:
           if (!capture_syscalls.syscall_open) {
               return True;
           }
           name = "open";
           count = 3;
           break;
       case __NR_close:
           if (!capture_syscalls.syscall_open) {
               return True;
           }
           name = "close";
           count = 1;
           break;
       default:
          return True;
    }

    char message[MAX_MESSAGE_BUFFER_LENGTH];

    tl_assert(count <= nArgs);

    switch (count) {
       case 0:
          VG_(snprintf)(message,
                        MAX_MESSAGE_BUFFER_LENGTH,
                        "SYSCALL %s\n",
                        name);
          break;
       case 1:
          VG_(snprintf)(message,
                        MAX_MESSAGE_BUFFER_LENGTH,
                        "SYSCALL %s %lu\n",
                        name, args[0]);
          break;
       case 2:
          VG_(snprintf)(message,
                        MAX_MESSAGE_BUFFER_LENGTH,
                        "SYSCALL %s %lu %lu\n",
                        name, args[0], args[1]);
          break;
       default:
         VG_(snprintf)(message,
                       MAX_MESSAGE_BUFFER_LENGTH,
                       "SYSCALL %s %lu %lu %lu\n",
                       name, args[0], args[1], args[2]);
         break;
    }
    write_message(message);
    capture_syscalls.drop_current_syscall = False;
    process_commands(CET_SYSCALL, NULL);
    if (capture_syscalls.drop_current_syscall) {
        *sysres = VG_(mk_SysRes_Success)(capture_syscalls.return_value);
       return False;
    }
    return True;
}

/*static
void post_syscall_wrap(ThreadId tid, UInt syscallno,
                       UWord* args, UInt nArgs, SysRes sys)
{
}*/

static void an_pre_clo_init(void)
{
   VG_(memset)(&capture_syscalls, 0, sizeof(capture_syscalls));
   VG_(memset)(&profile, 0, sizeof(profile));

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

   VG_(needs_command_line_options)(process_cmd_line_option,
                                   print_usage,
                                   print_debug_usage);

   VG_(needs_restore_thread)(restore_thread);

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

   VG_(track_new_mem_stack_signal) (new_mem_stack_signal);
   VG_(track_new_mem_stack) (new_mem_stack);
   VG_(track_die_mem_stack) (die_mem_stack);

   VG_(track_ban_mem_stack)       (ban_mem_stack);

   /*VG_(track_pre_mem_read)        (check_mem_is_defined );
   VG_(track_pre_mem_read_asciiz) (check_mem_is_defined_asciiz);
   VG_(track_pre_mem_write)       (check_mem_is_addressable);*/
   VG_(track_post_mem_write)      (post_mem_write);
   VG_(track_post_reg_write)                  (post_reg_write);
   VG_(track_post_reg_write_clientcall_return)(post_reg_write_clientcall);

   VG_(needs_client_requests) (an_handle_client_request);

   VG_(needs_syscall_control)(syscall_control);
}

VG_DETERMINE_INTERFACE_VERSION(an_pre_clo_init)

/*--------------------------------------------------------------------*/
/*--- end                                                          ---*/
/*--------------------------------------------------------------------*/
