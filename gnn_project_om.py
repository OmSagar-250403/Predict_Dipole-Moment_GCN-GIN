# -*- coding: utf-8 -*-
"""GNN_Project_Om.ipynb
Automatically generated by Colaboratory.

"""

import math
import numpy
import pandas as pd
import matplotlib.pylab as plt
from matplotlib.ticker import MaxNLocator
from pathlib import Path

import torch
import torch.nn.functional as Fun
from torch.nn import Linear, Sequential, BatchNorm1d, ReLU

from torch_geometric.datasets import QM9
from torch_geometric.nn import GCNConv, GINConv
from torch_geometric.loader import DataLoader
from torch_geometric.nn import global_mean_pool, global_add_pool

# specify the local data path
HERE = Path(_dh[-1])
DATA = HERE / "data"

# load dataset
qm9 = QM9(root=DATA)

import networkx as nx
import torch

# Hypothetical data
data = {
    'x': torch.tensor([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]]),
    'edge_index': torch.tensor([[0, 0, 1, 1, 2, 2, 3, 4], [1, 2, 3, 4, 0, 3, 4, 0]]),
    'edge_attr': torch.tensor([[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8], [0.9, 1.0, 1.1, 1.2],
                               [1.3, 1.4, 1.5, 1.6], [1.7, 1.8, 1.9, 2.0], [2.1, 2.2, 2.3, 2.4],
                               [2.5, 2.6, 2.7, 2.8], [2.9, 3.0, 3.1, 3.2]]),
    'y': torch.tensor([[42.0]]),
    'pos': torch.tensor([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 2.0]]),
    'idx': torch.tensor([0]),
    'name': 'gdb_1',
    'z': torch.tensor([0.5, 1.0, 1.5, 2.0, 2.5])
}

# Create a directed graph
graph = nx.DiGraph()

# Add nodes with features and positions
for i in range(data['x'].shape[0]):
    node_attributes = {'features': data['x'][i].tolist(), 'position': data['pos'][i].tolist(), 'node_attr': data['z'][i].item()}
    graph.add_node(i, **node_attributes)

# Add edges with attributes
for i in range(data['edge_index'].shape[1]):
    source, target = data['edge_index'][0][i].item(), data['edge_index'][1][i].item()
    edge_attributes = {'edge_attr': data['edge_attr'][i].tolist()}
    graph.add_edge(source, target, **edge_attributes)

# Visualize the graph (optional, requires matplotlib)
import matplotlib.pyplot as plt
pos = nx.spring_layout(graph)  # Adjust layout algorithm as needed
nx.draw(graph, pos, with_labels=True)
plt.show()

#from google.colab import drive
#drive.mount('/content/drive')

#path = "/content/drive/MyDrive/Bapi_sir_Project/Mol_Struc.csv"
#df = pd.read_csv(path)
#len(df)

# get one regression target
y_target = pd.DataFrame(qm9.data.y.numpy())
qm9.data.y = torch.Tensor(y_target[0])
qm9 = qm9.shuffle()

# data split
data_size = 900
train_index = int(data_size * 0.8)
test_index = train_index + int(data_size * 0.1)
val_index = test_index + int(data_size * 0.1)

# normalizing the data
data_mean = qm9.data.y[0:train_index].mean()              #mean
data_std = qm9.data.y[0:train_index].std()                #standard deviation
qm9.data.y = (qm9.data.y - data_mean) / data_std          #normal distribution

# datasets into DataLoader
train_loader = DataLoader(qm9[0:train_index], batch_size=64, shuffle=True)
test_loader = DataLoader(qm9[train_index:test_index], batch_size=64, shuffle=True)
val_loader = DataLoader(qm9[test_index:val_index], batch_size=64, shuffle=True)

"""# **Defining a GCN**"""

class GCN(torch.nn.Module):

    def __init__(self, dim_h):
        super().__init__()
        self.conv1 = GCNConv(qm9.num_features, dim_h)
        self.conv2 = GCNConv(dim_h, dim_h)
        self.conv3 = GCNConv(dim_h, dim_h)
        self.lin = torch.nn.Linear(dim_h, 1)

    def forward(self, data):
        e = data.edge_index
        x = data.x

        # First graph convolutional layer
        x = self.conv1(x, e)
        x = x.relu()

        # Second graph convolutional layer
        x = self.conv2(x, e)
        x = x.relu()

        # Third graph convolutional layer
        x = self.conv3(x, e)

        # Global mean pooling over nodes within each graph in the batch
        x = global_mean_pool(x, data.batch)

        # Dropout with a probability of 0.1 during training
        x = Fun.dropout(x, p=0.1, training=self.training)

        # Linear layer
        x = self.lin(x)

        return x

"""# **Defining a GIN**"""

class GIN(torch.nn.Module):
    """Graph Isomorphism Network class with 3 GINConv layers and 2 linear layers"""

    def __init__(self, dim_h):

        super(GIN, self).__init__()

        # First graph convolutional layer
        self.conv1 = GINConv(
            Sequential(Linear(11, dim_h), BatchNorm1d(dim_h), ReLU(), Linear(dim_h, dim_h), ReLU())
        )

        # Second graph convolutional layer
        self.conv2 = GINConv(
            Sequential(
                Linear(dim_h, dim_h), BatchNorm1d(dim_h), ReLU(), Linear(dim_h, dim_h), ReLU()
            )
        )

        # Third graph convolutional layer
        self.conv3 = GINConv(
            Sequential(
                Linear(dim_h, dim_h), BatchNorm1d(dim_h), ReLU(), Linear(dim_h, dim_h), ReLU()
            )
        )
        self.lin1 = Linear(dim_h, dim_h)
        self.lin2 = Linear(dim_h, 1)

    def forward(self, data):
        x = data.x
        edge_index = data.edge_index
        batch = data.batch

        # Node embeddings
        h = self.conv1(x, edge_index)
        h = h.relu()
        h = self.conv2(h, edge_index)
        h = h.relu()
        h = self.conv3(h, edge_index)

        # Graph-level readout
        h = global_add_pool(h, batch)

        h = self.lin1(h)
        h = h.relu()
        # backpropogation
        h = Fun.dropout(h, p=0.1, training=self.training)
        h = self.lin2(h)

        return h

torch.cuda.is_available()

"""# **Training a GNN**

***Training Set***
"""

def training(loader, model, loss, optimizer):
    """Training one epoch
    """
    model.train()

    current_loss = 0
    for d in loader:
        optimizer.zero_grad()
        d.x = d.x.float()

        out = model(d)

        l = loss(out, torch.reshape(d.y, (len(d.y), 1)))
        current_loss += l / len(loader)

        #back-propogation
        l.backward()
        optimizer.step()
    return current_loss, model

"""## ***Validation Set***"""

def validation(loader, model, loss):
    """Validation

    Args:
        loader (DataLoader): validation set in batches
        model (nn.Module): current trained model
        loss (nn.functional): loss function

    Returns:
        float: validation loss
    """
    model.eval()
    val_loss = 0
    for d in loader:
        out = model(d)
        l = loss(out, torch.reshape(d.y, (len(d.y), 1)))
        val_loss += l / len(loader)
    return val_loss

"""## ***Test Set***"""

@torch.no_grad()
def testing(loader, model):
    """Testing

    Args:
        loader (DataLoader): test dataset
        model (nn.Module): trained model

    Returns:
        float: test loss
    """
    loss = torch.nn.MSELoss()
    test_loss = 0
    test_target = numpy.empty((0))
    test_y_target = numpy.empty((0))
    for d in loader:
        out = model(d)
        # NOTE
        # out = out.view(d.y.size())
        l = loss(out, torch.reshape(d.y, (len(d.y), 1)))
        test_loss += l / len(loader)

        # save prediction vs ground truth values for plotting
        test_target = numpy.concatenate((test_target, out.detach().numpy()[:, 0]))
        test_y_target = numpy.concatenate((test_y_target, d.y.detach().numpy()))

    return test_loss, test_target, test_y_target

"""## ***Training Epochs*** ##"""

def train_epochs(epochs, model, train_loader, val_loader, path):
    """Training over all epochs

    Args:
        epochs (int): number of epochs to train for
        model (nn.Module): the current model
        train_loader (DataLoader): training data in batches
        val_loader (DataLoader): validation data in batches
        path (string): path to save the best model

    Returns:
        array: returning train and validation losses over all epochs, prediction and ground truth values for training data in the last epoch
    """

    #Optimizer and Loss
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=5e-4)
    loss = torch.nn.MSELoss()


    #Initialization and Tracking
    train_target = numpy.empty((0))
    train_y_target = numpy.empty((0))
    train_loss = numpy.empty(epochs)
    val_loss = numpy.empty(epochs)
    best_loss = math.inf


    #Training Loop
    for epoch in range(epochs):
        epoch_loss, model = training(train_loader, model, loss, optimizer)
        v_loss = validation(val_loader, model, loss)
        if v_loss < best_loss:
            torch.save(model.state_dict(), path)
        for d in train_loader:
            out = model(d)
            if epoch == epochs - 1:
                # record truly vs predicted values for training data from last epoch
                train_target = numpy.concatenate((train_target, out.detach().numpy()[:, 0]))
                train_y_target = numpy.concatenate((train_y_target, d.y.detach().numpy()))


        #Training and validation losses for each epoch are recorded.
        train_loss[epoch] = epoch_loss.detach().numpy()
        val_loss[epoch] = v_loss.detach().numpy()

        # print current train and val loss
        print(
            "Epoch: "
            + str(epoch)
            + ", Train loss: "
            + str(epoch_loss.item())
            + ", Val loss: "
            + str(v_loss.item())
            )
    return train_loss, val_loss, train_target, train_y_target

"""## ***Training GCN***"""

# training GCN for 10 epochs
epochs = 10

model = GCN(dim_h=128)

# Remember to change the path if you want to keep the previously trained model
gcn_train_loss, gcn_val_loss, gcn_train_target, gcn_train_y_target = train_epochs(
    epochs, model, train_loader, test_loader, "GCN_model.pt"
)

"""## ***Training GIN***"""

# Training GIN for 10 epochs
model = GIN(dim_h=64)

# Remember to change the path if you want to keep the previously trained model
gin_train_loss, gin_val_loss, gin_train_target, gin_train_y_target = train_epochs(
    epochs, model, train_loader, test_loader, "GIN_model.pt"
)

"""## **DEFINING PLOT LOSS**"""

def plot_loss(gcn_train_loss, gcn_val_loss, gin_train_loss, gin_val_loss):
    """Plot the loss for each epoch

    Args:
        epochs (int): number of epochs
        train_loss (array): training losses for each epoch
        val_loss (array): validation losses for each epoch
    """
    plt.plot(gcn_train_loss, label="Train loss (GCN)")
    plt.plot(gcn_val_loss, label="Val loss (GCN)")
    plt.plot(gin_train_loss, label="Train loss (GIN)")
    plt.plot(gin_val_loss, label="Val loss (GIN)")
    plt.legend()
    plt.ylabel("loss")
    plt.xlabel("epoch")
    plt.title("Model Loss")
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.show()

"""## **DEFINING PLOT TARGET**"""

def plot_targets(pred, ground_truth):
    """Plot true vs predicted value in a scatter plot

    Args:
        pred (array): predicted values
        ground_truth (array): ground truth values
    """
    f, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(pred, ground_truth, s=0.5)
    plt.xlim(-2, 7)
    plt.ylim(-2, 7)
    ax.axline((1, 1), slope=1)
    plt.xlabel("Predicted Value")
    plt.ylabel("Ground truth")
    plt.title("Ground truth vs prediction")
    plt.show()

# Plot overall losses of GIN and GCN

plot_loss(gcn_train_loss, gcn_val_loss, gin_train_loss, gin_val_loss)

# Plot target and prediction for training data

plot_targets(gcn_train_target, gcn_train_y_target)

# Plot target and prediction for training data

plot_targets(gin_train_target, gin_train_y_target)

# Calculate test loss from the best GCN model (according to validation loss)

# load our model
model = GCN(dim_h=128)
model.load_state_dict(torch.load("GCN_model.pt"))

# calculate test loss
gcn_test_loss, gcn_test_target, gcn_test_y = testing(test_loader, model)
print("Test Loss for GCN: " + str(gcn_test_loss.item()))

# plot prediction vs ground truth
plot_targets(gcn_test_target, gcn_test_y)

# Calculate test loss from the best GIN model (according to validation loss)

# load our model
model = GIN(dim_h=64)
model.load_state_dict(torch.load("GIN_model.pt"))

# calculate test loss
gin_test_loss, gin_test_target, gin_test_y = testing(test_loader, model)

print("Test Loss for GIN: " + str(gin_test_loss.item()))

# plot prediction vs ground truth
plot_targets(gin_test_target, gin_test_y)
