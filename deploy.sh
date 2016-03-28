#!/bin/bash

cd `dirname $0`

# Extrair pacote
tar -xzf package.tgz
rm package.tgz

# Substituir pacote
rm -rf GDGAjuBot_old
mv GDGAjuBot GDGAjuBot_old
mv build GDGAjuBot