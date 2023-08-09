filename = "src/lambda.h"
source = """
#ifndef _LAMBDA_H
#define _LAMBDA_H

#include <stddef.h>
#include <stdnoreturn.h>

typedef struct lambda lambda;
typedef struct lambda_header lambda_header;
typedef struct lambda_cont lambda_cont;
typedef lambda* lambda_impl(lambda* arg, lambda* self, lambda_cont* cont);
typedef void lambda_destructor(void * userdata);

// the header of a lambda function object
struct lambda_header {
    size_t refcount;
    size_t len_captures;
    size_t len_userdata;
    union {
        lambda_impl* impl;
        lambda* tail;
    };
};

// the lambda function object type
// a lambda function object with lexical captures and potentially user data
struct lambda {
    lambda_header header;
    lambda* captures[];
};

// the lambda continuation chain type
// a chain of pending lambda function continuations
struct lambda_cont {
    lambda_cont* next;
    lambda* fn;
};

// a bit flag in len_userdata that signifies a custom destructor
// the destructor is stored in the first 8 bytes of userdata
#define LAMBDA_USER_DESTRUCTOR 1

// a mask macro that selects userdata without the bit flags
#define LAMBDA_LEN_USERDATA(l) ((l)->len_userdata & ~LAMBDA_USER_DESTRUCTOR)

// create a statically allocated instance of a lambda
#define LAMBDA_INSTANCE(_name, _impl, _len_captures, _len_userdata, ...) \
    struct { \
        lambda_header header; \
        lambda* captures[_len_captures]; \
        char userdata[(_len_userdata) & ~LAMBDA_USER_DESTRUCTOR]; \
    } _name = { \
        .header = { \
            .refcount = 1, \
            .len_captures = _len_captures, \
            .len_userdata = _len_userdata, \
            .impl = _impl \
        }, \
        __VA_ARGS__ \
    }

// the lambda userdata accessor function
// defined by the lambda runtime
//
// this function returns a pointer to the userdata of the passed lambda
void* lambda_userdata(lambda* l);

// the lambda allocation failure handler
// default defined by the lambda runtime
// can be overridden
//
// this function is called when lambda_alloc fails
// this function does not return
noreturn void lambda_abort(void);

// the lambda memory allocation function
// default defined by the lambda runtime
// can be overridden
//
// allocates a contiguous buffer of size bytes
// calls lambda_abort on allocation failure
// used by the lambda runtime to allocate memory
//
// this function never returns NULL
void* lambda_mem_alloc(size_t size);

// the lambda deallocation function
// default defined by the lambda runtime
// can be overridden
//
// deallocates a contiguous buffer of size bytes allocated by lambda_mem_alloc
// used by the lambda runtime to deallocate memory
void lambda_mem_free(void* mem);

// the lambda allocation function
// defined by the lambda runtime
//
// allocates a lambda with len_captures captured lambdas and len_userdata bytes
// of user-supplied data, calls lambda_abort on allocation failure
//
// the members impl, captures, and userdata are uninitialized
lambda* lambda_alloc(size_t len_captures, size_t len_userdata);

// the continuation allocation function
// defined by the lambda runtime
//
// prepends the passed lambda to the passed continuation chain
// calls lambda_abort on allocation failure
lambda_cont* lambda_cont_alloc(lambda_cont* cont, lambda* l);

// the lambda reference-counting functions
// defined by the lambda runtime
//
// lambda_ref increments the refcount of the passed lambda by the passed amount
// lambda_unref decrements the refcount of the passed lambda
//
// when the refcount of the passed lambda reaches zero, it is deallocated and
// the refcounts of its captured lambdas are decremented
void lambda_ref(lambda* l, size_t count);
void lambda_unref(lambda* l);

// the lambda call function
// defined by the lambda runtime
//
// calls the first passed lambda with the second passed lambda as its argument
// continues with the passed continuation
lambda* lambda_call(lambda* fn, lambda* arg, lambda_cont* cont);

// the lambda continuation call function
// defined by the lambda runtime
//
// continues with the passed continuation, using the passed lambda as an
// argument
lambda* lambda_cont_call(lambda* arg, lambda_cont* cont);

// the blocking lambda call function
// defined by the lambda runtime
//
// calls the first passed lambda with the second passed lambda as its argument
// returns the result of the call
lambda* lambda_ret_call(lambda* fn, lambda* arg);

// the argumentless blocking lambda call function
// defined by the lambda runtime
//
// calls the first passed lambda with a dummy lambda as its argument
// returns the result of the call
lambda* lambda_null_call(lambda* fn);

#endif
""".strip()
