lambda_runtime_llir = """
target datalayout = "{data_layout}"
target triple = "{triple}"

%lambda_fn = type %lambda* (%lambda*, %lambda*, %lambda_cont*)
%lambda_cont = type {{ %lambda_cont*, %lambda* }}
%lambda_header = type {{ i{ptr_bits}, i{ptr_bits}, i{ptr_bits}, %lambda_fn* }}
%lambda = type {{ %lambda_header, [0 x %lambda*] }}

declare external void @lambda_abort() nounwind noreturn
declare external noalias nonnull i8* @lambda_mem_alloc(i{ptr_bits}) nounwind
declare external void @lambda_mem_free(i8* nocapture) nounwind
declare external void @lambda_unref(%lambda* nonnull nocapture) nounwind
declare external nonnull %lambda* @lambda_ret_call(%lambda* nonnull, %lambda* nonnull) nounwind
declare external nonnull %lambda* @lambda_null_call(%lambda* nonnull) nounwind

define available_externally noalias nonnull %lambda* @lambda_alloc(i{ptr_bits} %0, i{ptr_bits} %1) unnamed_addr nofree nounwind {{
    %3 = getelementptr %lambda, %lambda* null, i{ptr_bits} 0, i32 1, i{ptr_bits} %0
    %4 = ptrtoint %lambda** %3 to i{ptr_bits}
    %5 = add i{ptr_bits} %4, %1
    %6 = call i8* @lambda_mem_alloc(i{ptr_bits} %5)
    %7 = bitcast i8* %6 to %lambda*
    %8 = getelementptr inbounds %lambda, %lambda* %7, i{ptr_bits} 0, i32 0, i32 0
    store i{ptr_bits} 1, i{ptr_bits}* %8, align {ptr_align}
    %9 = getelementptr inbounds %lambda, %lambda* %7, i{ptr_bits} 0, i32 0, i32 1
    store i{ptr_bits} %0, i{ptr_bits}* %9, align {ptr_align}
    %10 = getelementptr inbounds %lambda, %lambda* %7, i{ptr_bits} 0, i32 0, i32 2
    store i{ptr_bits} %1, i{ptr_bits}* %10, align {ptr_align}
    ret %lambda* %7
}}

define available_externally noalias nonnull %lambda_cont* @lambda_cont_alloc(%lambda_cont* nonnull readonly %0, %lambda* nonnull readonly %1) unnamed_addr nofree nounwind {{
    %3 = getelementptr %lambda_cont, %lambda_cont* null, i{ptr_bits} 1
    %4 = ptrtoint %lambda_cont* %3 to i{ptr_bits}
    %5 = call i8* @lambda_mem_alloc(i{ptr_bits} %4)
    %6 = bitcast i8* %5 to %lambda_cont*
    %7 = getelementptr inbounds %lambda_cont, %lambda_cont* %6, i{ptr_bits} 0, i32 0
    store %lambda_cont* %0, %lambda_cont** %7, align {ptr_align}
    %8 =  getelementptr inbounds %lambda_cont, %lambda_cont* %6, i{ptr_bits} 0, i32 1
    store %lambda* %1, %lambda** %8, align {ptr_align}
    ret %lambda_cont* %6
}}

define available_externally void @lambda_ref(%lambda* nonnull nocapture %0, i{ptr_bits} %1) unnamed_addr argmemonly nofree nounwind {{
    %3 = getelementptr inbounds %lambda, %lambda* %0, i{ptr_bits} 0, i32 0, i32 0
    %4 = load i{ptr_bits}, i{ptr_bits}* %3, align {ptr_align}
    %5 = add i{ptr_bits} %4, %1
    store i{ptr_bits} %5, i{ptr_bits}* %3, align {ptr_align}
    ret void
}}

define available_externally nonnull i8* @lambda_userdata(%lambda* nonnull %0) unnamed_addr argmemonly nofree nounwind {{
    %2 = getelementptr inbounds %lambda, %lambda* %0, i{ptr_bits} 0, i32 0, i32 1
    %3 = load i{ptr_bits}, i{ptr_bits}* %2, align {ptr_align}
    %4 = getelementptr inbounds %lambda, %lambda* %0, i{ptr_bits} 0, i32 1, i{ptr_bits} %3
    %5 = bitcast %lambda** %4 to i8*
    ret i8* %5
}}

define available_externally nonnull %lambda* @lambda_call(%lambda* nonnull %0, %lambda* nonnull %1, %lambda_cont* nonnull %2) unnamed_addr nounwind {{
    %4 = getelementptr inbounds %lambda, %lambda* %0, i{ptr_bits} 0, i32 0, i32 3
    %5 = load %lambda* (%lambda*, %lambda*, %lambda_cont*)*, %lambda* (%lambda*, %lambda*, %lambda_cont*)** %4, align {ptr_align}
    %6 = tail call %lambda* %5(%lambda* %1, %lambda* %0, %lambda_cont* %2)
    ret %lambda* %6
}}

define available_externally nonnull %lambda* @lambda_cont_call(%lambda* nonnull %0, %lambda_cont* nonnull %1) unnamed_addr nounwind {{
    %3 = getelementptr inbounds %lambda_cont, %lambda_cont* %1, i{ptr_bits} 0, i32 0
    %4 = load %lambda_cont*, %lambda_cont** %3, align {ptr_align}
    %5 = getelementptr inbounds %lambda_cont, %lambda_cont* %1, i{ptr_bits} 0, i32 1
    %6 = load %lambda*, %lambda** %5, align {ptr_align}
    %7 = bitcast %lambda_cont* %1 to i8*
    call void @lambda_mem_free(i8* %7)
    %8 = tail call %lambda* @lambda_call(%lambda* %6, %lambda* %0, %lambda_cont* %4)
    ret %lambda* %8
}}
""".lstrip()
