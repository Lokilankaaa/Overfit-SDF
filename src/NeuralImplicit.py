import os
import time

import torch
import torch.optim as optim
from Renderer import Renderer
from SdfDataset import SdfDataset
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm


class NeuralImplicit:
    def __init__(self, N=16, H=64):
        self.model = self.OverFitSDF(N, H)
        self.epochs = 100
        self.lr = 1e-4
        self.batch_size = 128
        self.log_iterations = 1000

    def save(self, name):
        torch.save(self.model.state_dict(), name)

    def load(self, name):
        print('loading model...')
        self.model.load_state_dict(torch.load(name))

    def encode(self, mesh_file, early_stop=None, verbose=True):
        dataset = SdfDataset(mesh_file)
        dataloader = DataLoader(dataset=dataset, batch_size=self.batch_size, shuffle=True)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(device)

        loss_func = nn.L1Loss(reduction='sum')
        optimizer = optim.Adam(self.model.parameters(), lr=self.lr)

        for epoch in range(self.epochs):
            epoch_loss = 0
            self.model.train()
            count = 0
            bar = tqdm(dataloader)
            for batch_idx, (x_train, y_train) in enumerate(bar):
                x_train, y_train = x_train.to(device), y_train.to(device)
                count += self.batch_size
                optimizer.zero_grad()
                y_pred = self.model(x_train)
                loss = loss_func(y_pred, y_train)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

                bar.set_description("epoch:{} ".format(epoch))
                if verbose and count % 1000 == 0:
                    msg = '{}\t[{}/{}]\tepoch_loss: {:.6f}\tloss: {:.6f}'.format(
                        time.ctime(),
                        count,
                        len(dataset),
                        epoch_loss / (batch_idx + 1),
                        loss)
                    print(msg)

            if early_stop and epoch_loss < early_stop:
                break
            print('Saving model...')
            model_file = "./" + os.path.splitext(os.path.basename(mesh_file))[0] + ".pth"
            self.save(model_file)

    # Neural Network
    class OverFitSDF(nn.Module):
        def __init__(self, N, H):
            super().__init__()
            assert (N > 0)
            assert (H > 0)

            net = [nn.Linear(3, H), nn.LeakyReLU(0.1)]
            for i in range(0, N):
                net += [nn.Linear(H, H), nn.LeakyReLU(0.1)]
            net += [nn.Linear(H, 1), nn.LeakyReLU(0.1)]
            self.model = nn.Sequential(*net)

        def forward(self, x):
            x = self.model(x)
            output = torch.tanh(x)
            return output


if __name__ == '__main__':
    sdf = NeuralImplicit()
    sdf.encode('wave.sdf')
    sdf.load('_apple_entity_wave.pth')
    campos = torch.Tensor([0, 0, 2])
    at = torch.Tensor([0, 0, 0])
    width = 128
    height = 128
    tol = 0.001
    renderer = Renderer(sdf.model, campos, at, width, height, tol)
    renderer.render()
    # renderer.showImage()
    renderer.save('apple.png')
