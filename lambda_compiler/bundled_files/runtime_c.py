filename = "src/runtime.c"
source = r"""
#include <stddef.h>
#include <stdnoreturn.h>
#include <stdlib.h>

#include "lambda.h"

void* lambda_userdata(lambda* l) {
    return (void*) &l->captures[l->header.len_captures];
}

__attribute__((weak))
noreturn void lambda_abort(void) {
    abort();
}

__attribute__((weak))
void * lambda_mem_alloc(size_t size) {
    void * mem = malloc(size);
    if (mem == NULL) {
        lambda_abort();
    }
    return mem;
}

__attribute__((weak))
void lambda_mem_free(void * mem) {
    free(mem);
}

lambda* lambda_alloc(size_t len_captures, size_t len_userdata) {
    lambda* l = (lambda*) lambda_mem_alloc(
        sizeof (lambda) +
        sizeof (lambda*) * len_captures +
        len_userdata
    );

    l->header.refcount = 1;
    l->header.len_captures = len_captures;
    l->header.len_userdata = len_userdata;
    return l;
}

lambda_cont* lambda_cont_alloc(lambda_cont* cont, lambda* l) {
    lambda_cont* c = (lambda_cont*) lambda_mem_alloc(
        sizeof (lambda_cont)
    );

    c->next = cont;
    c->fn = l;
    return c;
}

void lambda_ref(lambda* l, size_t count) {
    l->header.refcount += count;
}

void lambda_unref(lambda* l) {
    if (l->header.refcount > 1) {
        l->header.refcount--;
        return;
    }

    if (LAMBDA_HAS_USER_DESTRUCTOR(l)) {
        void* userdata = lambda_userdata(l);
        ((lambda_destructor*)userdata)(userdata);
    }

    lambda* tail = NULL;
    if (l->header.refcount == 0) {
        tail = l->header.tail;
    }

    for (size_t i = 0; i < l->header.len_captures; i++) {
        lambda* cur = l->captures[i];
        if (cur->header.refcount > 1) {
            cur->header.refcount--;
            continue;
        }

        if (tail != NULL) {
            cur->header.refcount = 0;
            cur->header.tail = tail;
        }

        tail = cur;
    }

    lambda_mem_free(l);

    if (tail != NULL) {
        lambda_unref(tail);
    }
}

lambda* lambda_call(lambda* fn, lambda* arg, lambda_cont* cont) {
    return fn->header.impl(arg, fn, cont);
}

lambda* lambda_cont_call(lambda* arg, lambda_cont* cont) {
    lambda_cont* next = cont->next;
    lambda* fn = cont->fn;

    lambda_mem_free(cont);
    return lambda_call(fn, arg, next);
}

static lambda* lambda_ret_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(self);

    if (cont != NULL) {
        lambda_abort();
    }

    return arg;
}

static LAMBDA_INSTANCE(lambda_ret_inst, lambda_ret_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

static lambda* lambda_null_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(arg);
    return lambda_cont_call(self, cont);
}

static LAMBDA_INSTANCE(lambda_null_inst, lambda_null_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_ret_call(lambda* fn, lambda* arg) {
    lambda* ret = (lambda*)&lambda_ret_inst;
    lambda_ref(ret, 1);

    lambda_cont* cont = lambda_cont_alloc(NULL, ret);

    return lambda_call(fn, arg, cont);
}

lambda* lambda_null_call(lambda* fn) {
    lambda* null = (lambda*)&lambda_null_inst;
    lambda_ref(null, 1);

    return lambda_ret_call(fn, null);
}
""".strip()
