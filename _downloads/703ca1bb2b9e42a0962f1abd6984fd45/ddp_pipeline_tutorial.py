"""
Training Transformer models using Distributed Data Parallel and Pipeline Parallelism
====================================================================================

**Author**: `Pritam Damania <https://github.com/pritamdamania87>`_

This tutorial demonstrates how to train a large Transformer model across
multiple GPUs using `Distributed Data Parallel <https://pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html>`__ and
`Pipeline Parallelism <https://pytorch.org/docs/stable/pipeline.html>`__. This tutorial is an extension of the
`Sequence-to-Sequence Modeling with nn.Transformer and TorchText <https://pytorch.org/tutorials/beginner/transformer_tutorial.html>`__ tutorial
and scales up the same model to demonstrate how Distributed Data Parallel and
Pipeline Parallelism can be used to train Transformer models.

Prerequisites:

    * `Pipeline Parallelism <https://pytorch.org/docs/stable/pipeline.html>`__
    * `Sequence-to-Sequence Modeling with nn.Transformer and TorchText <https://pytorch.org/tutorials/beginner/transformer_tutorial.html>`__
    * `Getting Started with Distributed Data Parallel <https://pytorch.org/tutorials/intermediate/ddp_tutorial.html>`__
"""


######################################################################
# Define the model
# ----------------
#

######################################################################
# ``PositionalEncoding`` module injects some information about the
# relative or absolute position of the tokens in the sequence. The
# positional encodings have the same dimension as the embeddings so that
# the two can be summed. Here, we use ``sine`` and ``cosine`` functions of
# different frequencies.





























######################################################################
# In this tutorial, we will split a Transformer model across two GPUs and use
# pipeline parallelism to train the model. In addition to this, we use
# `Distributed Data Parallel <https://pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html>`__
# to train two replicas of this pipeline. We have one process driving a pipe across
# GPUs 0 and 1 and another process driving a pipe across GPUs 2 and 3. Both these
# processes then use Distributed Data Parallel to train the two replicas. The
# model is exactly the same model used in the `Sequence-to-Sequence Modeling with nn.Transformer and TorchText
# <https://pytorch.org/tutorials/beginner/transformer_tutorial.html>`__ tutorial,
# but is split into two stages. The largest number of parameters belong to the
# `nn.TransformerEncoder <https://pytorch.org/docs/stable/generated/torch.nn.TransformerEncoder.html>`__ layer.
# The `nn.TransformerEncoder <https://pytorch.org/docs/stable/generated/torch.nn.TransformerEncoder.html>`__
# itself consists of ``nlayers`` of `nn.TransformerEncoderLayer <https://pytorch.org/docs/stable/generated/torch.nn.TransformerEncoderLayer.html>`__.
# As a result, our focus is on ``nn.TransformerEncoder`` and we split the model
# such that half of the ``nn.TransformerEncoderLayer`` are on one GPU and the
# other half are on another. To do this, we pull out the ``Encoder`` and
# ``Decoder`` sections into seperate modules and then build an nn.Sequential
# representing the original Transformer module.


















































######################################################################
# Start multiple processes for training
# -------------------------------------
#


######################################################################
# We start two processes where each process drives its own pipeline across two
# GPUs. ``run_worker`` is executed for each process.




######################################################################
# Load and batch data
# -------------------
#


######################################################################
# The training process uses Wikitext-2 dataset from ``torchtext``. The
# vocab object is built based on the train dataset and is used to numericalize
# tokens into tensors. Starting from sequential data, the ``batchify()``
# function arranges the dataset into columns, trimming off any tokens remaining
# after the data has been divided into batches of size ``batch_size``.
# For instance, with the alphabet as the sequence (total length of 26)
# and a batch size of 4, we would divide the alphabet into 4 sequences of
# length 6:
#
# .. math::
#   \begin{bmatrix}
#   \text{A} & \text{B} & \text{C} & \ldots & \text{X} & \text{Y} & \text{Z}
#   \end{bmatrix}
#   \Rightarrow
#   \begin{bmatrix}
#   \begin{bmatrix}\text{A} \\ \text{B} \\ \text{C} \\ \text{D} \\ \text{E} \\ \text{F}\end{bmatrix} &
#   \begin{bmatrix}\text{G} \\ \text{H} \\ \text{I} \\ \text{J} \\ \text{K} \\ \text{L}\end{bmatrix} &
#   \begin{bmatrix}\text{M} \\ \text{N} \\ \text{O} \\ \text{P} \\ \text{Q} \\ \text{R}\end{bmatrix} &
#   \begin{bmatrix}\text{S} \\ \text{T} \\ \text{U} \\ \text{V} \\ \text{W} \\ \text{X}\end{bmatrix}
#   \end{bmatrix}
#
# These columns are treated as independent by the model, which means that
# the dependence of ``G`` and ``F`` can not be learned, but allows more
# efficient batch processing.
#

# In 'run_worker'













































######################################################################
# Functions to generate input and target sequence
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#


######################################################################
# ``get_batch()`` function generates the input and target sequence for
# the transformer model. It subdivides the source data into chunks of
# length ``bptt``. For the language modeling task, the model needs the
# following words as ``Target``. For example, with a ``bptt`` value of 2,
# we’d get the following two Variables for ``i`` = 0:
#
# .. image:: ../_static/img/transformer_input_target.png
#
# It should be noted that the chunks are along dimension 0, consistent
# with the ``S`` dimension in the Transformer model. The batch dimension
# ``N`` is along dimension 1.
#

# In 'run_worker'







######################################################################
# Model scale and Pipe initialization
# -----------------------------------
#


######################################################################
# To demonstrate training large Transformer models using pipeline parallelism,
# we scale up the Transformer layers appropriately. We use an embedding
# dimension of 4096, hidden size of 4096, 16 attention heads and 8 total
# transformer layers (``nn.TransformerEncoderLayer``). This creates a model with
# **~1 billion** parameters.
#
# We need to initialize the `RPC Framework <https://pytorch.org/docs/stable/rpc.html>`__
# since Pipe depends on the RPC framework via `RRef <https://pytorch.org/docs/stable/rpc.html#rref>`__
# which allows for future expansion to cross host pipelining. We need to
# initialize the RPC framework with only a single worker since we're using a
# single process to drive multiple GPUs.
#
# The pipeline is then initialized with 8 transformer layers on one GPU and 8
# transformer layers on the other GPU. One pipe is setup across GPUs 0 and 1 and
# another across GPUs 2 and 3. Both pipes are then replicated using DistributedDataParallel.

# In 'run_worker'



































































######################################################################
# Run the model
# -------------
#


######################################################################
# `CrossEntropyLoss <https://pytorch.org/docs/master/nn.html?highlight=crossentropyloss#torch.nn.CrossEntropyLoss>`__
# is applied to track the loss and
# `SGD <https://pytorch.org/docs/master/optim.html?highlight=sgd#torch.optim.SGD>`__
# implements stochastic gradient descent method as the optimizer. The initial
# learning rate is set to 5.0. `StepLR <https://pytorch.org/docs/master/optim.html?highlight=steplr#torch.optim.lr_scheduler.StepLR>`__ is
# applied to adjust the learn rate through epochs. During the
# training, we use
# `nn.utils.clip_grad_norm\_ <https://pytorch.org/docs/master/nn.html?highlight=nn%20utils%20clip_grad_norm#torch.nn.utils.clip_grad_norm_>`__
# function to scale all the gradient together to prevent exploding.
#

# In 'run_worker'



























































######################################################################
# Loop over epochs. Save the model if the validation loss is the best
# we've seen so far. Adjust the learning rate after each epoch.

# In 'run_worker'





















######################################################################
# Evaluate the model with the test dataset
# -------------------------------------
#
# Apply the best model to check the result with the test dataset.

# In 'run_worker'






# Main execution







######################################################################
# Output
# ------
#


######################################################################
#.. code-block:: py
#
#    [RANK 1]: Total parameters in model: 1,041,453,167
#    [RANK 0]: Total parameters in model: 1,041,453,167
#    [RANK 0]: | epoch   1 |    10/   50 batches | lr 5.00 | ms/batch 1414.18 | loss 48.70 | ppl 1406154472673147092992.00
#    [RANK 1]: | epoch   1 |    10/   50 batches | lr 5.00 | ms/batch 1414.42 | loss 48.49 | ppl 1146707511057334927360.00
#    [RANK 0]: | epoch   1 |    20/   50 batches | lr 5.00 | ms/batch 1260.76 | loss 42.74 | ppl 3648812398518492672.00
#    [RANK 1]: | epoch   1 |    20/   50 batches | lr 5.00 | ms/batch 1260.76 | loss 41.51 | ppl 1064844757565813248.00
#    [RANK 0]: | epoch   1 |    30/   50 batches | lr 5.00 | ms/batch 1246.80 | loss 41.85 | ppl 1497706388552644096.00
#    [RANK 1]: | epoch   1 |    30/   50 batches | lr 5.00 | ms/batch 1246.80 | loss 40.46 | ppl 373830103285747072.00
#    [RANK 0]: | epoch   1 |    40/   50 batches | lr 5.00 | ms/batch 1246.69 | loss 39.76 | ppl 185159839078666368.00
#    [RANK 1]: | epoch   1 |    40/   50 batches | lr 5.00 | ms/batch 1246.69 | loss 39.89 | ppl 211756997625874912.00
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 0]: | end of epoch   1 | time: 69.37s | valid loss  2.92 | valid ppl    18.46
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 1]: | end of epoch   1 | time: 69.39s | valid loss  2.92 | valid ppl    18.46
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 1]: | epoch   2 |    10/   50 batches | lr 4.51 | ms/batch 1373.91 | loss 39.77 | ppl 187532281612905856.00
#    [RANK 0]: | epoch   2 |    10/   50 batches | lr 4.51 | ms/batch 1375.62 | loss 39.05 | ppl 91344349371016336.00
#    [RANK 0]: | epoch   2 |    20/   50 batches | lr 4.51 | ms/batch 1250.33 | loss 30.62 | ppl 19917977906884.78
#    [RANK 1]: | epoch   2 |    20/   50 batches | lr 4.51 | ms/batch 1250.33 | loss 30.48 | ppl 17250186491252.32
#    [RANK 1]: | epoch   2 |    30/   50 batches | lr 4.51 | ms/batch 1250.73 | loss 29.14 | ppl 4534527326854.47
#    [RANK 0]: | epoch   2 |    30/   50 batches | lr 4.51 | ms/batch 1250.73 | loss 29.43 | ppl 6035762659681.65
#    [RANK 0]: | epoch   2 |    40/   50 batches | lr 4.51 | ms/batch 1249.54 | loss 23.11 | ppl 10869828323.89
#    [RANK 1]: | epoch   2 |    40/   50 batches | lr 4.51 | ms/batch 1249.55 | loss 22.90 | ppl 8785318464.24
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 0]: | end of epoch   2 | time: 69.02s | valid loss  0.94 | valid ppl     2.55
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 1]: | end of epoch   2 | time: 69.05s | valid loss  0.94 | valid ppl     2.55
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 0]: | epoch   3 |    10/   50 batches | lr 4.29 | ms/batch 1380.66 | loss 12.98 | ppl 434052.59
#    [RANK 1]: | epoch   3 |    10/   50 batches | lr 4.29 | ms/batch 1376.47 | loss 12.92 | ppl 410203.33
#    [RANK 1]: | epoch   3 |    20/   50 batches | lr 4.29 | ms/batch 1250.88 | loss  9.80 | ppl 18034.58
#    [RANK 0]: | epoch   3 |    20/   50 batches | lr 4.29 | ms/batch 1250.88 | loss  9.78 | ppl 17741.88
#    [RANK 0]: | epoch   3 |    30/   50 batches | lr 4.29 | ms/batch 1251.89 | loss 10.37 | ppl 32016.45
#    [RANK 1]: | epoch   3 |    30/   50 batches | lr 4.29 | ms/batch 1251.90 | loss 10.46 | ppl 34735.08
#    [RANK 0]: | epoch   3 |    40/   50 batches | lr 4.29 | ms/batch 1250.70 | loss 10.09 | ppl 24147.61
#    [RANK 1]: | epoch   3 |    40/   50 batches | lr 4.29 | ms/batch 1250.71 | loss 10.08 | ppl 23748.31
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 0]: | end of epoch   3 | time: 69.12s | valid loss  0.69 | valid ppl     2.00
#    [RANK 0]: -----------------------------------------------------------------------------------------
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 1]: | end of epoch   3 | time: 69.12s | valid loss  0.69 | valid ppl     2.00
#    [RANK 1]: -----------------------------------------------------------------------------------------
#    [RANK 0]: =========================================================================================
#    [RANK 0]: | End of training | test loss  0.60 | test ppl     1.83
#    [RANK 0]: =========================================================================================
#    [RANK 1]: =========================================================================================
#    [RANK 1]: | End of training | test loss  0.60 | test ppl     1.83

# %%%%%%RUNNABLE_CODE_REMOVED%%%%%%