# Go ABI — Reading Arguments and Structures

Reference for `function_prototype`, `variable_name`, `variable_type` and `type_definition` claims against a Go ELF. Every statement here was verified against a real sample; the addresses are that sample's and are examples of the pattern, not constants to reuse.

Binary Ninja does not model the Go register ABI. It applies a sysv-flavoured convention, so its `argN` numbering, its parameter count and some of its variables are artifacts. Map by **register**, never by index.

---

## The goroutine pointer

`r14` holds the current goroutine pointer `g`. `g.stackguard0` is at `+0x10`.

Every non-leaf Go function opens with a stack-growth check comparing `g.stackguard0` against the lowest frame address the function will touch:

```c
if (&__return_addr u<= g[2])        // small frame
if (&__saved_rbp   u>  *(g + 0x10)) // inverted sense
if (&var_110       u<= g[2])        // larger frame, deeper local
```

Three things vary and none of them change the meaning:

- **The compared operand.** `&__return_addr` for a small frame; a deeper local (`&var_110`, `&var_50`, `&__saved_rbp`) once the frame is large enough that the deepest touched address is what matters.
- **The dereference form.** `g[2]` on an `int64_t*` and `*(g + 0x10)` are the same field.
- **The branch sense.** `u<=` means the guard branch itself calls the growth helper. `u>` means the in-bounds case enters the body and the growth path falls through at the **tail** of the function. Read the sense before describing what the check guards — a claim that says "the guard branch calls morestack" is false for the inverted form.

A leaf function that touches no stack beyond its own registers has no check and **no `r14` parameter at all**. Its absence is a fact about the function, not an oversight.

### Pinning the layout independently

The r14-holds-`g` fact is an ABI assertion. It can be corroborated from the binary alone, which is what an evidence-gated claim needs:

- The growth helper at `0x4681a0` sets `edx = 0` and tail-jumps to the real `runtime.morestack` at `0x468120`. pclntab records `func_id 13` (`FuncID_morestack`) at `0x468120`.
- `0x468120` loads `g` from `fs:-8` — the TLS slot — and writes the `gobuf` fields at `+0x38` (`sched.sp`), `+0x40` (`sched.pc`), `+0x50` (`sched.ctxt`) and `+0x68` (`sched.bp`) while reading `g.m` at `+0x30`. That field constellation is `runtime.g`, and it places `stackguard0` at `+0x10`.
- A sleep routine re-fetched its `r14` argument from `*(fsbase - 8)` after an intervening call, proving `r14` and the TLS `g` slot hold the same pointer.

Cite the mechanism, not the convention. `0x4681a0` is `runtime.morestack_noctxt`; calling it `runtime.morestack` is a checkable falsehood and grounds for rejection.

---

## Argument registers

Integer arguments go in this order:

```
RAX, RBX, RCX, RDI, RSI, R8, R9, R10, R11    then g in r14
```

Binary Ninja's `argN` names do not follow it. Get the real mapping from the prototype's register annotations and the parameter storage:

```bash
$BNPY $SKILL/bn_lane_query.py CASE_DIR/work/analyst.bndb --vars 0xVA
```

A parameter annotated `@ r14` is `g`. A parameter with no annotation still sits in a specific register — resolve it from the call-site disassembly, not from its index.

### Slices occupy three slots

A `[]byte` parameter is passed as `ptr, len, cap` in three consecutive registers. One Go slice parameter therefore looks like three Binary Ninja parameters, and a function taking three slices presents as nine integer arguments plus `g`.

The capacity register is what tells you whether the slice is a whole array or a window into a larger one:

```asm
mov   esi, 0x20        ; len = 32
mov   r8, rsi          ; cap = len   -> standalone array
```

```asm
mov   esi, 0x20        ; len = 32
mov   r8d, 0x1000      ; cap = 4096  -> subslice of a 4096-byte backing array
```

`cap` copied straight from the `len` register means a standalone array, where `cap == len`. A divergent `cap` means a subslice, and the value is the distance from the subslice start to the **end of the backing array**. For a 4096-byte blob:

- `key = blob[0:32]` → `ptr = blob`, `len = 0x20`, `cap = 0x1000`
- `iv = blob[32:48]` → `ptr = blob + 0x20`, `len = 0x10`, `cap = 0xfe0` (`0x1000 - 0x20`)

This is the difference between "the two call sites contradict each other" and "the two call sites tell you the parameter is a capacity". A capacity that cannot be a length or a buffer size — `0xfe0` for a 16-byte IV — is positive evidence, not noise.

---

## pclntab

Useful, and not literal in a tampered binary.

- The `file` field frequently survives garbling and is quotable as attribution. `name` and `package` are hashed by garble and must **not** be quoted as if they named the function; a package field reading `zZGbwt` is not evidence the function is in the runtime.
- Derive behaviour from code. Use pclntab to corroborate, never as the sole basis.
- `func_id` values are enum ordinals whose meaning depends on the Go version. `18` is `FuncID_runtime_main` in the Go 1.23+ enum; in 1.22 and earlier the same ordinal is `FuncID_sigpanic`. Establish the Go version before reading any `func_id`, and corroborate an ordinal against a second function in the same binary before relying on it.

`evidence/go_pclntab.json` carries the parsed table; `evidence/go_context.json` carries the version estimate and its basis.

---

## What not to name

Binary Ninja's convention invents parameters and variables that do not exist in the machine code.

**Phantom parameters.** Go's `main.main` takes no arguments, but Binary Ninja presents `arg1` and `arg2` alongside the real `g` because it sees `rax`/`rbx` read before write. The sole caller — `runtime.main` — never sets them. They stay unnamed. Recording *why* in a `function_comment` is the correct outcome, not naming them.

**Phantom variables.** Under the sysv convention every callee clobbers `rdi`/`rsi`/`rdx`, so Binary Ninja materialises variables for registers the function never touches. One 26-instruction function presented an `rdi` variable while not a single instruction referenced RDI. The tell: a variable redefined by *every* call and never read on its own account. Before naming any register variable, confirm the register is actually dereferenced or stored.
