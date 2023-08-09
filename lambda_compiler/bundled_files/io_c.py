filename = "src/io.c"
source = r"""
#include <stdio.h>
#include "lambda.h"

static lambda* lambda_io_true_2_0_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_ref(self->captures[0], 1);
    lambda_unref(arg);
    lambda* value = self->captures[0];
    lambda_unref(self);
    return lambda_cont_call(value, cont);
}

static lambda* lambda_io_true_1_0_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda* value = lambda_alloc(1, 0);
    value->header.impl = lambda_io_true_2_0_impl;
    value->captures[0] = arg;
    lambda_unref(self);
    return lambda_cont_call(value, cont);
}

LAMBDA_INSTANCE(lambda_io_true_0_inst, lambda_io_true_1_0_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_true = (lambda*)&lambda_io_true_0_inst;

static lambda* lambda_io_false_2_0_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(self);
    return lambda_cont_call(arg, cont);
}

LAMBDA_INSTANCE(lambda_io_false_0_inst, lambda_io_false_2_0_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

static lambda* lambda_io_false_1_0_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_ref((lambda*)&lambda_io_false_0_inst, 1);
    lambda_unref(arg);
    lambda_unref(self);
    return lambda_cont_call((lambda*)&lambda_io_false_0_inst, cont);
}

LAMBDA_INSTANCE(lambda_io_false_1_inst, lambda_io_false_1_0_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_false = (lambda*)&lambda_io_false_1_inst;

static lambda* lambda_io_error_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(arg);
    return lambda_cont_call(self, cont);
}

LAMBDA_INSTANCE(lambda_io_error_inst, lambda_io_error_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_error = (lambda*)&lambda_io_error_inst;

static lambda* num_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(arg);

    return lambda_cont_call(self, cont);
}

static lambda* mk_num(size_t n) {
    lambda* l = lambda_alloc(0, sizeof (size_t));
    l->header.impl = num_impl;

    *(size_t*)lambda_userdata(l) = n;

    return l;
}

static size_t get_num(lambda* l) {
    if (l->header.len_userdata != sizeof (size_t)) return -1;

    return *(size_t*)lambda_userdata(l);
}

static lambda* lambda_io_zero_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    lambda_unref(arg);
    lambda_unref(self);
    lambda_ref(lambda_io_error, 1);
    return lambda_cont_call(lambda_io_error, cont);
}

LAMBDA_INSTANCE(lambda_io_zero_inst, lambda_io_zero_impl, 0, 8,
    .captures = {},
    .userdata = {0, 0, 0, 0, 0, 0, 0, 0}
);

lambda* lambda_io_zero = (lambda*)&lambda_io_zero_inst;

static lambda* lambda_io_succ_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    size_t num = get_num(arg);
    lambda* r = mk_num(num + 1);

    lambda_unref(arg);
    lambda_unref(self);

    return lambda_cont_call(r, cont);
}

LAMBDA_INSTANCE(lambda_io_succ_inst, lambda_io_succ_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_succ = (lambda*)&lambda_io_succ_inst;

static lambda* lambda_io_pred_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    size_t num = get_num(arg);
    lambda* r = mk_num(num - 1);

    lambda_unref(arg);
    lambda_unref(self);

    return lambda_cont_call(r, cont);
}

LAMBDA_INSTANCE(lambda_io_pred_inst, lambda_io_pred_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_pred = (lambda*)&lambda_io_pred_inst;

static lambda* lambda_io_iszero_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    size_t num = get_num(arg);

    lambda_unref(arg);
    lambda_unref(self);

    lambda* r;
    if (num == 0) {
        r = lambda_io_true;
    } else {
        r = lambda_io_false;
    }

    lambda_ref(r, 1);
    return lambda_cont_call(r, cont);
}

LAMBDA_INSTANCE(lambda_io_iszero_inst, lambda_io_iszero_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_iszero = (lambda*)&lambda_io_iszero_inst;

static lambda* lambda_io_putc_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    size_t num = get_num(arg);

    putchar(num);

    lambda_unref(arg);
    lambda_unref(self);

    lambda_ref(lambda_io_error, 1);
    return lambda_cont_call(lambda_io_error, cont);
}

LAMBDA_INSTANCE(lambda_io_putc_inst, lambda_io_putc_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_putc = (lambda*)&lambda_io_putc_inst;

static lambda* lambda_io_getc_impl(lambda* arg, lambda* self, lambda_cont* cont) {
    int c = getchar();

    size_t num;
    if (c == EOF) {
        num = 256;
    } else {
        num = c;
    }

    lambda* r = mk_num(num);

    lambda_unref(arg);
    lambda_unref(self);

    return lambda_cont_call(r, cont);
}

LAMBDA_INSTANCE(lambda_io_getc_inst, lambda_io_getc_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_getc = (lambda*)&lambda_io_getc_inst;

static lambda* lambda_io_debug_impl(lambda* arg, lambda* self, lambda_cont* cont) {
#if __x86_64__ || __i386__
    __asm__("int3");
#endif

    lambda_unref(arg);
    lambda_unref(self);

    lambda_ref(lambda_io_error, 1);
    return lambda_cont_call(lambda_io_error, cont);
}

LAMBDA_INSTANCE(lambda_io_debug_inst, lambda_io_debug_impl, 0, 0,
    .captures = {},
    .userdata = {}
);

lambda* lambda_io_debug = (lambda*)&lambda_io_debug_inst;
""".strip()
